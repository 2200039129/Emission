# Data Model

This prototype uses a Django API with an append-friendly emissions ledger. The core idea is to preserve every source row exactly as received, create a normalized review record beside it, and make approved records immutable for audit.

## Entities

### Tenant

`Tenant` owns all operational data. Every source, batch, raw row, normalized row, factor, and audit event is queried through a tenant boundary.

Important fields:

- `slug`: stable tenant key used in API paths such as `/api/tenants/acme-industrials/records/`.
- `name`: display name.

Production notes:

- Use row-level security or tenant-scoped managers if this moved to Postgres.
- Add tenant membership and roles for analyst, approver, and admin.

### SourceSystem

`SourceSystem` represents the enterprise system and parser contract.

Supported source types:

- `sap_flat_file`: SAP MM fuel/procurement export.
- `utility_csv`: electricity account or interval/bill export.
- `concur_json`: SAP Concur itinerary/travel export.

Important fields:

- `tenant`: prevents one tenant from seeing another tenant's sources.
- `source_type`: selects the parser.
- `config`: parser options such as plant-code mapping, meter mapping, locale, and emission-region settings.

### IngestionBatch

`IngestionBatch` is the auditable intake event. A batch groups rows uploaded or pasted together.

Important fields:

- `tenant` and `source`: trace where the batch came from.
- `filename`: optional file name or integration label.
- `payload_sha256`: detects duplicate uploads and proves source-payload integrity.
- `parser_version`: explains which normalizer created the rows.
- `received_at`: chain-of-custody timestamp.

### RawRecord

`RawRecord` stores the original row payload and parse errors. It is intentionally not overwritten.

Important fields:

- `batch`: points to the intake event.
- `row_number`: source row number for analyst reconciliation.
- `external_id`: document number, meter id, trip id, or booking id when available.
- `raw_payload`: original source fields as JSON.
- `parse_errors`: structural parse failures.

### NormalizedRecord

`NormalizedRecord` is the analyst-facing record. It converts source-specific rows into one schema for Scope 1, 2, and 3 activity.

Important fields:

- `tenant`: tenant boundary for fast scoped queries.
- `raw_record`: one-to-one link to the preserved source row.
- `scope`: `scope_1`, `scope_2`, or `scope_3`.
- `activity_type`: fuel, electricity, flight, hotel, or ground transport.
- `activity_label`: human-readable description.
- `facility_or_traveler`: plant, meter, site, or traveler.
- `period_start` and `period_end`: supports utility billing periods that are not calendar months.
- `raw_quantity` and `raw_unit`: original measurement.
- `normalized_quantity` and `normalized_unit`: normalized measurement used for factor application.
- `emission_factor_key`: versioned factor reference.
- `emissions_kg_co2e`: calculated result.
- `status`: `needs_review`, `suspicious`, `failed`, or `approved_locked`.
- `issues`: parser warnings and anomaly flags.
- `locked_at` and `locked_by`: approval lock metadata.

Locking rule:

- `approve_and_lock()` refuses failed rows and sets `approved_locked` plus `locked_at`.
- Locked rows should not be edited. Corrections should be reversal or amendment batches so the audit trail remains intact.

### EmissionFactor

`EmissionFactor` stores factor metadata separately from normalized rows.

Important fields:

- `key`: stable versioned reference copied onto `NormalizedRecord`.
- `scope` and `activity_type`: what the factor applies to.
- `denominator_unit`: required normalized unit such as `gal`, `kWh`, `passenger-km`, or `room-night`.
- `factor`: kg CO2e per denominator unit.
- `source`, `valid_from`, `valid_to`: factor provenance and validity window.

Prototype factors are simplified. A production system would store factor gases, geography, market/location basis, cabin class, radiative forcing policy, and supplier-specific electricity instruments.

### AuditEvent

`AuditEvent` records review actions.

Important fields:

- `tenant`: tenant-scoped audit query.
- `record`: record affected, nullable for batch-level events.
- `actor`: user who took the action when authenticated.
- `action`: for example `approve_and_lock` or `flag_suspicious`.
- `before` and `after`: JSON snapshots of changed review fields.
- `reason`: analyst explanation.
- `created_at`: immutable event timestamp.

## Normalization Rules

The service keeps source units and normalized units:

- Liters, litres, and litros to gallons for liquid fuel.
- Cubic meters to cubic feet for natural gas.
- Electricity to kWh.
- Miles to kilometers for ground transport.
- Flight distance to passenger-km.
- Hotel nights to room-night.

Dates are parsed from ISO, US slash dates, European dot dates, short-year variants, and Japanese-style year/month/day strings.

## Scope Coverage

- Scope 1: SAP fuel/procurement rows, including diesel, gasoline, and natural gas purchases consumed by owned or controlled facilities/assets.
- Scope 2: utility electricity consumption with billing period start and end dates.
- Scope 3: business travel flights, hotels, and ground transportation.

## API Shape

- `GET /api/health/`
- `GET /api/tenants/{tenant_slug}/records/`
- `POST /api/tenants/{tenant_slug}/ingestions/`
- `POST /api/records/{id}/approve/`
- `POST /api/records/{id}/flag/`

The frontend currently runs a client-side mirror of the normalizers for demo responsiveness, while the Django backend contains the same API boundaries and persistence model.