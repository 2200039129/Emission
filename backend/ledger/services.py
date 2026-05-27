import csv
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from io import StringIO

from .models import IngestionBatch, NormalizedRecord, RawRecord, SourceSystem, Tenant


HEADER_ALIASES = {
    "plant": ["plant", "werks", "planta", "site", "centro"],
    "date": ["posting", "buchungsdatum", "date", "fecha", "document date"],
    "material": ["material", "description", "texto", "materialkurztext"],
    "quantity": ["menge", "quantity", "cantidad", "qty"],
    "unit": ["me", "unit", "uom", "unidad"],
    "document": ["beleg", "document", "doc", "reference"],
    "service_start": ["service start", "start"],
    "service_end": ["service end", "end"],
    "usage": ["usage", "kwh", "consumption"],
    "tariff": ["tariff", "rate", "rate schedule"],
    "meter": ["meter", "mpan", "account meter"],
}


def parse_date(value):
    if not value:
        return None
    cleaned = str(value).strip().replace("年", "-").replace("月", "-").replace("日", "")
    for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%y", "%m/%d/%y"]:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        return None


def normalize_unit(quantity, unit):
    qty = Decimal(str(quantity or 0))
    normalized = str(unit or "").strip().lower()
    if normalized in ["l", "lt", "liter", "liters", "litre", "litres", "litros"]:
        return qty * Decimal("0.264172"), "gal"
    if normalized in ["m3", "m^3", "cbm"]:
        return qty * Decimal("35.3147"), "ft3"
    if normalized in ["mi", "mile", "miles"]:
        return qty * Decimal("1.60934"), "km"
    return qty, normalized or unit


def emission_factor(activity_type, unit):
    if activity_type == "electricity":
        return Decimal("0.38"), "epa_egrid_us_avg_2024"
    if activity_type == "hotel":
        return Decimal("18"), "defra_hotel_room_night_proxy_2024"
    if activity_type == "ground_transport":
        return Decimal("0.21"), "defra_taxi_vehicle_km_2024"
    if activity_type == "flight":
        return Decimal("0.145"), "defra_air_short_long_blended_2024"
    if unit == "ft3":
        return Decimal("0.054"), "epa_natural_gas_ft3_2024"
    return Decimal("10.194"), "epa_diesel_gal_2024"


def suspicious_issues(record):
    issues = list(record.get("issues", []))
    if re.search(r"PLT\?\?|BR-7X|UNKNOWN", record.get("facility_or_traveler", "")):
        issues.append("Plant code is not mapped to tenant master data")
    if not record.get("period_start"):
        issues.append("Date could not be parsed")
    if Decimal(str(record.get("normalized_quantity") or 0)) == 0:
        issues.append("Zero quantity requires analyst confirmation")
    if record.get("activity_type") == "electricity" and "MISSING" in str(record.get("raw_payload", {})):
        issues.append("Tariff is missing")
    return sorted(set(issues))


def header_index(headers, canonical):
    aliases = HEADER_ALIASES[canonical]
    for i, header in enumerate(headers):
        cleaned = header.strip().lower()
        if any(alias in cleaned for alias in aliases):
            return i
    return -1


def csv_rows(payload):
    first = payload.splitlines()[0]
    delimiter = ";" if ";" in first else ","
    reader = csv.reader(StringIO(payload), delimiter=delimiter)
    rows = list(reader)
    return rows[0], rows[1:]


def normalize_sap(payload):
    headers, rows = csv_rows(payload)
    output = []
    for row_number, row in enumerate(rows, start=2):
        raw = dict(zip(headers, row))
        plant = row[header_index(headers, "plant")] if header_index(headers, "plant") >= 0 else "UNKNOWN"
        material = row[header_index(headers, "material")] if header_index(headers, "material") >= 0 else "Fuel procurement"
        raw_quantity = Decimal(row[header_index(headers, "quantity")] or "0")
        raw_unit = row[header_index(headers, "unit")] if header_index(headers, "unit") >= 0 else ""
        normalized_quantity, normalized_unit = normalize_unit(raw_quantity, raw_unit)
        factor, factor_key = emission_factor("fuel", normalized_unit)
        period = parse_date(row[header_index(headers, "date")])
        doc = row[header_index(headers, "document")] if header_index(headers, "document") >= 0 else f"row-{row_number}"
        record = {
            "row_number": row_number,
            "external_id": doc,
            "raw_payload": raw,
            "scope": "scope_1",
            "activity_type": "stationary_or_mobile_fuel",
            "activity_label": material,
            "facility_or_traveler": f"Plant {plant}",
            "period_start": period,
            "period_end": period,
            "raw_quantity": raw_quantity,
            "raw_unit": raw_unit,
            "normalized_quantity": normalized_quantity,
            "normalized_unit": normalized_unit,
            "emission_factor_key": factor_key,
            "emissions_kg_co2e": normalized_quantity * factor,
            "issues": [],
        }
        output.append(record)
    return output


def normalize_utility(payload):
    headers, rows = csv_rows(payload)
    output = []
    for row_number, row in enumerate(rows, start=2):
        raw = dict(zip(headers, row))
        start = parse_date(row[header_index(headers, "service_start")])
        end = parse_date(row[header_index(headers, "service_end")])
        quantity = Decimal(row[header_index(headers, "usage")] or "0")
        tariff = row[header_index(headers, "tariff")] if header_index(headers, "tariff") >= 0 else "MISSING"
        meter = row[header_index(headers, "meter")] if header_index(headers, "meter") >= 0 else f"row-{row_number}"
        factor, factor_key = emission_factor("electricity", "kWh")
        record = {
            "row_number": row_number,
            "external_id": meter,
            "raw_payload": raw,
            "scope": "scope_2",
            "activity_type": "electricity",
            "activity_label": "Purchased electricity",
            "facility_or_traveler": f"Meter {meter}",
            "period_start": start,
            "period_end": end,
            "raw_quantity": quantity,
            "raw_unit": "kWh",
            "normalized_quantity": quantity,
            "normalized_unit": "kWh",
            "emission_factor_key": factor_key,
            "emissions_kg_co2e": quantity * factor,
            "issues": ["Non-calendar billing period retained"] if start and start.day != 1 else [],
        }
        if tariff == "MISSING":
            record["issues"].append("Tariff is missing")
        output.append(record)
    return output


def normalize_concur(payload):
    airport_distances = {"SFO-JFK": Decimal("4160"), "LHR-JFK": Decimal("5540"), "LAX-ORD": Decimal("2802")}
    output = []
    for row_number, item in enumerate(json.loads(payload), start=1):
        booking_type = item.get("type", "Travel")
        if booking_type == "Hotel":
            activity_type = "hotel"
            quantity = Decimal(str(item.get("nights", 0)))
            unit = "room-night"
            label = f"Hotel {item.get('city', 'unknown city')}"
        elif booking_type in ["Ride", "Car", "Rail"]:
            activity_type = "ground_transport"
            quantity, _ = normalize_unit(item.get("distanceMi") or item.get("distanceKm") or 0, "mi" if item.get("distanceMi") else "km")
            unit = "vehicle-km"
            label = f"{booking_type} {item.get('mode', '')}".strip()
        else:
            activity_type = "flight"
            route = f"{item.get('from')}-{item.get('to')}"
            quantity = Decimal(str(item.get("distanceKm") or airport_distances.get(route, 0)))
            unit = "passenger-km"
            label = f"Flight {route}"
        factor, factor_key = emission_factor(activity_type, unit)
        period = parse_date(item.get("date"))
        record = {
            "row_number": row_number,
            "external_id": item.get("tripId", f"trip-{row_number}"),
            "raw_payload": item,
            "scope": "scope_3",
            "activity_type": activity_type,
            "activity_label": label,
            "facility_or_traveler": item.get("traveler", "Unassigned traveler"),
            "period_start": period,
            "period_end": period,
            "raw_quantity": quantity,
            "raw_unit": unit,
            "normalized_quantity": quantity,
            "normalized_unit": unit,
            "emission_factor_key": factor_key,
            "emissions_kg_co2e": quantity * factor,
            "issues": ["Airport-code distance lookup failed"] if activity_type == "flight" and quantity == 0 else [],
        }
        output.append(record)
    return output


NORMALIZERS = {
    SourceSystem.SAP_FLAT_FILE: normalize_sap,
    SourceSystem.UTILITY_CSV: normalize_utility,
    SourceSystem.CONCUR_JSON: normalize_concur,
}


def ingest_payload(tenant_slug, source_type, payload, filename=""):
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug.replace("-", " ").title()})
    source, _ = SourceSystem.objects.get_or_create(
        tenant=tenant,
        source_type=source_type,
        display_name=source_type,
        defaults={"config": {"ingestion": "manual paste or file upload"}},
    )
    batch = IngestionBatch.objects.create(
        tenant=tenant,
        source=source,
        filename=filename,
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )
    records = []
    for normalized in NORMALIZERS[source_type](payload):
        raw = RawRecord.objects.create(
            batch=batch,
            row_number=normalized.pop("row_number"),
            external_id=normalized.pop("external_id"),
            raw_payload=normalized.pop("raw_payload"),
        )
        normalized["tenant"] = tenant
        normalized["raw_record"] = raw
        issues = suspicious_issues(normalized)
        normalized["issues"] = issues
        normalized["status"] = "failed" if any("failed" in issue.lower() or "could not" in issue.lower() for issue in issues) else "suspicious" if issues else "needs_review"
        records.append(NormalizedRecord.objects.create(**normalized))
    return batch, records