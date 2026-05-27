import { useMemo, useState } from "react";

type Source = "sap_flat_file" | "utility_csv" | "concur_json";
type Status = "needs_review" | "failed" | "suspicious" | "approved_locked";

type RecordRow = {
  id: string;
  tenant: string;
  source: Source;
  scope: "Scope 1" | "Scope 2" | "Scope 3";
  activity: string;
  siteOrTraveler: string;
  startDate: string;
  endDate: string;
  rawValue: string;
  normalizedValue: number;
  normalizedUnit: string;
  emissionsKg: number;
  status: Status;
  issues: string[];
  locked: boolean;
};

const sourceLabels: Record<Source, string> = {
  sap_flat_file: "SAP MM flat file",
  utility_csv: "Utility interval CSV",
  concur_json: "Concur itinerary JSON",
};

const samples: Record<Source, string> = {
  sap_flat_file: `Werks;Buchungsdatum;Material;Menge;ME;Beleg;Lieferant
DE01;31.01.2025;Diesel fuer Stapler;1200;L;4900008123;ENERGIE AG
BR-7X;01/02/25;Natural Gas;140;M3;4900008124;Gas Sul
PLT??;2025年02月03日;Gasoline;88;GAL;4900008125;Fuel Co`,
  utility_csv: `Account,Meter,Service Start,Service End,Usage,Tariff,Unit,Peak kW
88120,MT-100,2025-01-16,2025-02-15,18420,TOU-GS-3,kWh,142
88120,MT-101,02/16/2025,03/17/2025,0,TOU-GS-3,kWh,0
88120,MT-102,2025-03-18,2025-04-15,245,MISSING,kWh,9`,
  concur_json: `[
  {"tripId":"T-4481","traveler":"Maya Patel","type":"Air","from":"SFO","to":"JFK","date":"2025-02-12","distanceKm":4160,"cabin":"economy"},
  {"tripId":"T-4481","traveler":"Maya Patel","type":"Hotel","city":"New York","nights":3,"date":"2025-02-12"},
  {"tripId":"T-4481","traveler":"Maya Patel","type":"Ride","mode":"Taxi","distanceMi":18,"date":"02/15/2025"},
  {"tripId":"T-4900","traveler":"Ken Ito","type":"Air","from":"LHR","to":"ZZZ","date":"2025-03-02"}
]`,
};

const initialRows: RecordRow[] = [
  {
    id: "sap-4900008123-1",
    tenant: "acme-industrials",
    source: "sap_flat_file",
    scope: "Scope 1",
    activity: "Diesel fuer Stapler",
    siteOrTraveler: "Plant DE01",
    startDate: "2025-01-31",
    endDate: "2025-01-31",
    rawValue: "1200 L",
    normalizedValue: 317.01,
    normalizedUnit: "gal",
    emissionsKg: 3231.7,
    status: "needs_review",
    issues: [],
    locked: false,
  },
  {
    id: "sap-4900008124-1",
    tenant: "acme-industrials",
    source: "sap_flat_file",
    scope: "Scope 1",
    activity: "Natural Gas",
    siteOrTraveler: "Plant BR-7X",
    startDate: "2025-02-01",
    endDate: "2025-02-01",
    rawValue: "140 M3",
    normalizedValue: 4944.05,
    normalizedUnit: "ft3",
    emissionsKg: 267.0,
    status: "suspicious",
    issues: ["Plant code does not match approved ERP plant pattern"],
    locked: false,
  },
  {
    id: "util-88120-feb",
    tenant: "acme-industrials",
    source: "utility_csv",
    scope: "Scope 2",
    activity: "Purchased electricity",
    siteOrTraveler: "Meter MT-100",
    startDate: "2025-01-16",
    endDate: "2025-02-15",
    rawValue: "18420 kWh, TOU-GS-3",
    normalizedValue: 18420,
    normalizedUnit: "kWh",
    emissionsKg: 6999.6,
    status: "needs_review",
    issues: ["Non-calendar billing period prorated by service dates"],
    locked: false,
  },
  {
    id: "travel-T-4481-air",
    tenant: "acme-industrials",
    source: "concur_json",
    scope: "Scope 3",
    activity: "Flight SFO to JFK",
    siteOrTraveler: "Maya Patel",
    startDate: "2025-02-12",
    endDate: "2025-02-12",
    rawValue: "4160 km economy",
    normalizedValue: 4160,
    normalizedUnit: "passenger-km",
    emissionsKg: 603.2,
    status: "needs_review",
    issues: [],
    locked: false,
  },
  {
    id: "travel-T-4900-air",
    tenant: "acme-industrials",
    source: "concur_json",
    scope: "Scope 3",
    activity: "Flight LHR to ZZZ",
    siteOrTraveler: "Ken Ito",
    startDate: "2025-03-02",
    endDate: "2025-03-02",
    rawValue: "airport-code lookup failed",
    normalizedValue: 0,
    normalizedUnit: "passenger-km",
    emissionsKg: 0,
    status: "failed",
    issues: ["Unknown destination airport code", "Distance required before emission factor can be applied"],
    locked: false,
  },
];

function parseDate(value: string) {
  const cleaned = value.trim().replace(/[年月]/g, "-").replace(/日/g, "");
  const direct = new Date(cleaned);
  if (!Number.isNaN(direct.valueOf())) return direct.toISOString().slice(0, 10);
  const parts = cleaned.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$/);
  if (!parts) return "";
  const year = parts[3].length === 2 ? `20${parts[3]}` : parts[3];
  const dayFirst = cleaned.includes(".");
  const month = dayFirst ? parts[2] : parts[1];
  const day = dayFirst ? parts[1] : parts[2];
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function normalizeUnit(value: number, unit: string, activity = "") {
  const normalized = unit.toLowerCase().replace(/liters?|ltr|litr?os?/g, "l");
  if (["l", "lt"].includes(normalized)) return { value: value * 0.264172, unit: "gal" };
  if (["m3", "m^3"].includes(normalized)) return { value: value * 35.3147, unit: "ft3" };
  if (["mi", "mile", "miles"].includes(normalized)) return { value: value * 1.60934, unit: activity.includes("Ride") ? "vehicle-km" : "km" };
  return { value, unit: normalized || unit };
}

function suspiciousFor(row: RecordRow) {
  const issues = [...row.issues];
  if (/PLT\?\?|BR-7X/.test(row.siteOrTraveler)) issues.push("Plant code requires mapping to tenant master data");
  if (row.normalizedValue === 0) issues.push("Zero activity is unusual for a billable record");
  if (row.source === "utility_csv" && !row.rawValue.includes("TOU")) issues.push("Tariff missing or not recognized");
  if (!row.startDate) issues.push("Date could not be parsed");
  return Array.from(new Set(issues));
}

function parsePayload(source: Source, payload: string): RecordRow[] {
  if (source === "concur_json") {
    const airportKm: Record<string, number> = { "SFO-JFK": 4160, "LHR-JFK": 5540, "LAX-ORD": 2802 };
    const records = JSON.parse(payload) as Array<Record<string, string | number>>;
    return records.map((item, index) => {
      const type = String(item.type || "Travel");
      const date = parseDate(String(item.date || ""));
      let distanceKm = Number(item.distanceKm || 0);
      if (!distanceKm && item.distanceMi) distanceKm = Number(item.distanceMi) * 1.60934;
      if (!distanceKm && item.from && item.to) distanceKm = airportKm[`${item.from}-${item.to}`] || 0;
      const factor = type === "Hotel" ? 18 : type === "Ride" ? 0.21 : 0.145;
      const quantity = type === "Hotel" ? Number(item.nights || 0) : distanceKm;
      const row: RecordRow = {
        id: `travel-${item.tripId || "new"}-${index}`,
        tenant: "acme-industrials",
        source,
        scope: "Scope 3",
        activity: type === "Air" ? `Flight ${item.from || "?"} to ${item.to || "?"}` : `${type} ${item.city || item.mode || "booking"}`,
        siteOrTraveler: String(item.traveler || "Unassigned traveler"),
        startDate: date,
        endDate: date,
        rawValue: type === "Hotel" ? `${quantity} nights` : `${distanceKm.toFixed(0)} km`,
        normalizedValue: Number(quantity.toFixed(2)),
        normalizedUnit: type === "Hotel" ? "room-night" : type === "Ride" ? "vehicle-km" : "passenger-km",
        emissionsKg: Number((quantity * factor).toFixed(1)),
        status: "needs_review",
        issues: !distanceKm && type === "Air" ? ["Airport-code distance lookup failed"] : [],
        locked: false,
      };
      const issues = suspiciousFor(row);
      return { ...row, issues, status: issues.length ? (row.emissionsKg ? "suspicious" : "failed") : "needs_review" };
    });
  }

  const [headerLine, ...lines] = payload.trim().split(/\r?\n/);
  const delimiter = headerLine.includes(";") ? ";" : ",";
  const headers = headerLine.split(delimiter).map((h) => h.trim().toLowerCase());
  const find = (names: string[]) => headers.findIndex((h) => names.some((name) => h.includes(name)));

  return lines.filter(Boolean).map((line, index) => {
    const cells = line.split(delimiter).map((c) => c.trim());
    if (source === "sap_flat_file") {
      const plant = cells[find(["werks", "plant", "planta", "site"])] || "UNKNOWN";
      const date = parseDate(cells[find(["buchungsdatum", "posting", "date", "fecha"])] || "");
      const activity = cells[find(["material", "description", "texto"])] || "Fuel procurement";
      const qty = Number(cells[find(["menge", "quantity", "cantidad"])] || 0);
      const unit = cells[find(["me", "unit", "uom"])] || "";
      const doc = cells[find(["beleg", "document", "doc"])] || `row-${index}`;
      const normalized = normalizeUnit(qty, unit, activity);
      const factor = activity.toLowerCase().includes("gas") && normalized.unit === "ft3" ? 0.054 : 10.194;
      const row: RecordRow = {
        id: `sap-${doc}-${index}`,
        tenant: "acme-industrials",
        source,
        scope: "Scope 1",
        activity,
        siteOrTraveler: `Plant ${plant}`,
        startDate: date,
        endDate: date,
        rawValue: `${qty} ${unit}`,
        normalizedValue: Number(normalized.value.toFixed(2)),
        normalizedUnit: normalized.unit,
        emissionsKg: Number((normalized.value * factor).toFixed(1)),
        status: "needs_review",
        issues: [],
        locked: false,
      };
      const issues = suspiciousFor(row);
      return { ...row, issues, status: issues.length ? "suspicious" : "needs_review" };
    }

    const start = parseDate(cells[find(["service start", "start"])] || "");
    const end = parseDate(cells[find(["service end", "end"])] || start);
    const kwh = Number(cells[find(["usage", "kwh"])] || 0);
    const tariff = cells[find(["tariff", "rate"])] || "MISSING";
    const meter = cells[find(["meter"])] || `row-${index}`;
    const row: RecordRow = {
      id: `util-${meter}-${index}`,
      tenant: "acme-industrials",
      source,
      scope: "Scope 2",
      activity: "Purchased electricity",
      siteOrTraveler: `Meter ${meter}`,
      startDate: start,
      endDate: end,
      rawValue: `${kwh} kWh, ${tariff}`,
      normalizedValue: kwh,
      normalizedUnit: "kWh",
      emissionsKg: Number((kwh * 0.38).toFixed(1)),
      status: "needs_review",
      issues: start.slice(8) !== "01" ? ["Non-calendar billing period preserved for proration"] : [],
      locked: false,
    };
    const issues = suspiciousFor(row);
    return { ...row, issues, status: issues.length ? (kwh ? "suspicious" : "failed") : "needs_review" };
  });
}

export default function App() {
  const [rows, setRows] = useState<RecordRow[]>(initialRows);
  const [source, setSource] = useState<Source>("sap_flat_file");
  const [payload, setPayload] = useState(samples.sap_flat_file);
  const [selectedId, setSelectedId] = useState(initialRows[1].id);
  const selected = rows.find((row) => row.id === selectedId) || rows[0];
  const totals = useMemo(
    () => ({
      review: rows.filter((row) => row.status === "needs_review").length,
      failed: rows.filter((row) => row.status === "failed").length,
      locked: rows.filter((row) => row.locked).length,
      kg: rows.reduce((sum, row) => sum + row.emissionsKg, 0),
    }),
    [rows],
  );

  function ingest() {
    try {
      const parsed = parsePayload(source, payload);
      setRows((current) => [...parsed, ...current]);
      setSelectedId(parsed[0]?.id || selectedId);
    } catch {
      setRows((current) => [
        {
          id: `failed-${Date.now()}`,
          tenant: "acme-industrials",
          source,
          scope: source === "utility_csv" ? "Scope 2" : source === "concur_json" ? "Scope 3" : "Scope 1",
          activity: "Payload parse failed",
          siteOrTraveler: "Upload batch",
          startDate: "",
          endDate: "",
          rawValue: "unreadable payload",
          normalizedValue: 0,
          normalizedUnit: "unknown",
          emissionsKg: 0,
          status: "failed",
          issues: ["Parser could not read this sample. Check delimiter, JSON shape, or required headers."],
          locked: false,
        },
        ...current,
      ]);
    }
  }

  function updateRecord(id: string, status: Status) {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, status, locked: status === "approved_locked" } : row)));
  }

  return (
    <main className="min-h-screen bg-[#f5f1e8] text-[#1e2a21]">
      <section className="grid min-h-screen grid-cols-1 lg:grid-cols-[360px_1fr]">
        <aside className="border-r border-[#1e2a21]/15 bg-[#d8e2c3] p-8 lg:min-h-screen">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#52613d]">Carbon ledger prototype</p>
          <h1 className="mt-5 text-5xl font-semibold leading-none tracking-tight">Traceable emissions intake for analysts</h1>
          <p className="mt-5 text-base leading-7 text-[#52613d]">
            A Django API and React review console for messy SAP fuel, utility electricity, and corporate travel records.
          </p>

          <div className="mt-10 grid grid-cols-2 gap-x-8 gap-y-6 border-y border-[#1e2a21]/15 py-7">
            <Metric label="Review" value={totals.review.toString()} />
            <Metric label="Failed" value={totals.failed.toString()} />
            <Metric label="Locked" value={totals.locked.toString()} />
            <Metric label="kg CO2e" value={Math.round(totals.kg).toLocaleString()} />
          </div>

          <div className="mt-9 space-y-4">
            <h2 className="text-xl font-semibold">Ingest source</h2>
            <select
              value={source}
              onChange={(event) => {
                const next = event.target.value as Source;
                setSource(next);
                setPayload(samples[next]);
              }}
              className="w-full border border-[#1e2a21]/20 bg-[#f5f1e8] px-4 py-3 text-sm outline-none focus:border-[#1e2a21]"
            >
              {Object.entries(sourceLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <textarea
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              className="h-56 w-full border border-[#1e2a21]/20 bg-[#f5f1e8] p-4 font-mono text-xs leading-5 outline-none focus:border-[#1e2a21]"
            />
            <button onClick={ingest} className="w-full bg-[#1e2a21] px-5 py-4 text-sm font-semibold text-white transition hover:bg-[#52613d]">
              Normalize sample batch
            </button>
          </div>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="flex flex-col justify-between gap-4 border-b border-[#1e2a21]/15 px-6 py-5 md:flex-row md:items-end">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-[#52613d]">Tenant: acme-industrials</p>
              <h2 className="mt-2 text-3xl font-semibold">Review queue</h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-[#52613d]">
              Approving a row locks it. Locked records can be amended only through a reversal batch and an audit event in the backend model.
            </p>
          </header>

          <div className="grid flex-1 grid-cols-1 xl:grid-cols-[1fr_380px]">
            <div className="overflow-auto">
              <table className="w-full min-w-[920px] border-collapse text-left text-sm">
                <thead className="sticky top-0 bg-[#f5f1e8] text-xs uppercase tracking-[0.16em] text-[#52613d]">
                  <tr className="border-b border-[#1e2a21]/15">
                    <th className="px-6 py-4 font-semibold">Status</th>
                    <th className="px-6 py-4 font-semibold">Source</th>
                    <th className="px-6 py-4 font-semibold">Activity</th>
                    <th className="px-6 py-4 font-semibold">Period</th>
                    <th className="px-6 py-4 font-semibold">Normalized</th>
                    <th className="px-6 py-4 font-semibold">Emissions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => setSelectedId(row.id)}
                      className={`cursor-pointer border-b border-[#1e2a21]/10 transition hover:bg-white/45 ${selected?.id === row.id ? "bg-white/65" : ""}`}
                    >
                      <td className="px-6 py-5"><StatusLabel status={row.status} /></td>
                      <td className="px-6 py-5 text-[#52613d]">{sourceLabels[row.source]}</td>
                      <td className="px-6 py-5">
                        <div className="font-medium">{row.activity}</div>
                        <div className="mt-1 text-xs text-[#52613d]">{row.scope} / {row.siteOrTraveler}</div>
                      </td>
                      <td className="px-6 py-5 text-[#52613d]">{row.startDate || "Unparsed"}{row.endDate && row.endDate !== row.startDate ? ` to ${row.endDate}` : ""}</td>
                      <td className="px-6 py-5">{row.normalizedValue.toLocaleString()} {row.normalizedUnit}</td>
                      <td className="px-6 py-5 font-medium">{row.emissionsKg.toLocaleString()} kg</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <aside className="border-l border-[#1e2a21]/15 bg-[#eee5d4] p-6">
              <p className="text-xs uppercase tracking-[0.22em] text-[#52613d]">Record detail</p>
              <h3 className="mt-3 text-2xl font-semibold">{selected.activity}</h3>
              <dl className="mt-7 space-y-5 text-sm">
                <Detail label="Record ID" value={selected.id} />
                <Detail label="Raw value" value={selected.rawValue} />
                <Detail label="Normalized" value={`${selected.normalizedValue} ${selected.normalizedUnit}`} />
                <Detail label="CO2e" value={`${selected.emissionsKg} kg`} />
                <Detail label="Lock state" value={selected.locked ? "Approved and immutable" : "Editable review row"} />
              </dl>

              <div className="mt-8 border-t border-[#1e2a21]/15 pt-6">
                <h4 className="font-semibold">Validation notes</h4>
                {selected.issues.length ? (
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-[#8a4b22]">
                    {selected.issues.map((issue) => <li key={issue}>{issue}</li>)}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-[#52613d]">No parser errors or anomaly flags.</p>
                )}
              </div>

              <div className="mt-8 grid grid-cols-2 gap-3">
                <button
                  disabled={selected.locked || selected.status === "failed"}
                  onClick={() => updateRecord(selected.id, "approved_locked")}
                  className="bg-[#1e2a21] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#1e2a21]/30"
                >
                  Approve and lock
                </button>
                <button
                  disabled={selected.locked}
                  onClick={() => updateRecord(selected.id, "suspicious")}
                  className="border border-[#1e2a21]/30 px-4 py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Mark suspicious
                </button>
              </div>
            </aside>
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-3xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-[0.18em] text-[#52613d]">{label}</div>
    </div>
  );
}

function StatusLabel({ status }: { status: Status }) {
  const text = status === "approved_locked" ? "approved locked" : status.replace("_", " ");
  const color = status === "failed" ? "text-red-700" : status === "suspicious" ? "text-amber-700" : status === "approved_locked" ? "text-green-800" : "text-[#52613d]";
  return <span className={`font-semibold uppercase tracking-[0.14em] ${color}`}>{text}</span>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-4 border-b border-[#1e2a21]/10 pb-3">
      <dt className="text-[#52613d]">{label}</dt>
      <dd className="break-words font-medium">{value}</dd>
    </div>
  );
}