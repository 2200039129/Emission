# Decisions

## SAP Source Choice

I chose an SAP MM flat-file export instead of IDoc, OData, or BAPI.

Why:

- Enterprise sustainability teams often receive scheduled SAP extracts from ABAP jobs, SAP GUI exports, or data warehouse jobs before they receive direct integration credentials.
- Flat files expose realistic messiness: translated column names, semicolon delimiters in European locales, inconsistent date formats, and local unit labels.
- The prototype can be reviewed without requiring SAP system access, OAuth setup, RFC connectivity, or IDoc schema imports.

Supported subset:

- Fuel and procurement rows from SAP Materials Management style exports.
- Fields equivalent to plant, posting/document date, material description, quantity, unit of measure, document number, and supplier.
- German, English, Spanish, and partial multilingual header aliases for important columns.
- Liquid fuel in liters or gallons and natural gas in cubic meters.

Not supported:

- Full IDoc segment parsing.
- SAP pricing conditions, reversals, purchase order lifecycle status, GR/IR matching, and valuation classes.
- Direct SAP OData authentication or delta tokens.

## Utility Source Choice

I chose CSV export for electricity data.

Why:

- Commercial utility portals and Green Button-style data-access portals commonly allow CSV export of interval or billing consumption.
- CSV makes billing-period boundaries explicit and avoids unreliable PDF extraction in a short prototype.
- A utility API would be better long term, but authentication and utility-by-utility schemas would dominate the exercise.

Supported subset:

- Account, meter, service start, service end, usage, unit, tariff, and peak kW columns.
- kWh normalization.
- Non-calendar periods such as January 16 to February 15 are preserved and flagged for proration/reporting logic.
- Missing tariffs are flagged because tariff drives cost review and sometimes market-based Scope 2 evidence.

## Travel Source Choice

I modeled SAP Concur itinerary JSON rather than Navan.

Why:

- Concur documentation describes trip queries by start/end date, booking type, user, and segments such as Air, Car, Hotel, Rail, Ride, and Parking.
- A JSON itinerary payload is more realistic for an API pull than forcing analysts to upload spreadsheet exports for travel.
- Concur is common in large enterprises, and travel records naturally demonstrate different factors per category.

Supported subset:

- Air, Hotel, and Ride/ground transport records.
- Flight emissions use passenger-km, hotel emissions use room-night, and ride emissions use vehicle-km.
- If distance is missing but airport codes are present, the parser attempts a route lookup.
- Unknown airport routes become failed or suspicious records requiring analyst review.

## Ingestion Method

The prototype supports manual paste/file-like payload submission to `POST /api/tenants/{tenant}/ingestions/`.

Why:

- It exercises parser and normalization behavior without requiring credentials to SAP, Concur, or a utility portal.
- It supports analyst review of real sample payloads.
- It keeps deployment simple for a prototype while preserving the API shape needed for later scheduled pulls.

## Ambiguities Resolved

- Approved rows are immutable. Corrections should be new reversal/amendment batches, not edits to locked rows.
- Suspicious rows are still normalized when possible; failed rows are created when required fields prevent calculation.
- Plant codes are not auto-corrected unless a tenant mapping exists. Strange codes are flagged.
- Utility billing periods are stored as actual service periods, not forced into calendar months.
- Emissions are stored in kg CO2e even when the activity unit differs.

## Questions For The PM

- Which emission-factor libraries must be accepted for reporting: EPA, DEFRA, IEA, supplier-specific, or customer-provided?
- Should Scope 2 support both location-based and market-based calculations in the first release?
- What is the approval workflow: single analyst approval, maker/checker, or audit committee lock?
- What tenant isolation level is contractually required: app-level scoping, separate schemas, or separate databases?
- Which source systems are first customer-critical: SAP ECC, S/4HANA Cloud, Concur, Navan, Workday, Coupa, or utility portals?
- Are corrections expected as reversals, overwrite-with-version, or formal restatements?

## Intentionally Ignored

- Authentication and role management beyond model hooks.
- Real factor-library imports.
- Full deployment automation with managed Postgres.
- PDF bill extraction.
- Automated SAP/Concur/utility credential flows.