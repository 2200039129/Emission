# Sources

## SAP Fuel And Procurement

Researched:

- SAP IDoc structure and export behavior.
- SAP OData purchase-order and purchase-requisition API examples.
- Typical SAP MM fields around plant, material, quantity, unit, document, supplier, and posting date.

Real-world format studied:

- IDocs contain control records and data records with segments such as `EDI_DC40`, `E1EDK01`, and `E1EDP01`; they may be exported as XML or text.
- SAP S/4HANA exposes OData APIs such as purchase order and purchase requisition services with fields like plant, company code, requested quantity, base unit, and purchasing group.
- I selected flat-file export because it is a common operational handoff from SAP MM or reporting jobs and gives a realistic prototype without SAP credentials.

Why the sample data is realistic:

- Uses German headers such as `Werks`, `Buchungsdatum`, `Menge`, and `ME`.
- Uses semicolon delimiters, which are common in European spreadsheet exports.
- Contains document-like numbers, plant codes, supplier names, fuel descriptions, liters, gallons, and cubic meters.
- Includes strange plant codes and Japanese-style dates to exercise messy enterprise exports.

Limitations and breakages:

- Does not parse actual IDoc segment payloads.
- Does not validate material master data or SAP unit codes through SAP customizing tables.
- Does not understand reversals, goods movement types, or purchase-order status.
- Header aliasing is intentionally small and would need tenant-specific mapping.

References consulted:

- ecosio, "Structure and segments of an INVOIC IDoc in SAP ERP", about IDoc control/data/status records and segment examples.
- SAP API examples and community documentation for S/4HANA OData purchase order and purchase requisition endpoints.

## Utility Electricity

Researched:

- Commercial electric bill anatomy.
- Green Button or portal CSV exports for interval or account usage.
- Billing periods, kWh consumption, tariffs/rate schedules, and peak kW demand.

Real-world format studied:

- CSV exports from utility portals or Green Button-style data access rather than PDF bills.
- Rows include account, meter, service start, service end, usage, unit, tariff, and peak kW.

Why the sample data is realistic:

- Billing periods are not calendar months, such as January 16 to February 15.
- Tariffs look like commercial time-of-use rate schedules.
- Peak kW is present because commercial bills often include demand charges.
- Missing tariff and zero consumption rows are included as analyst review cases.

Limitations and breakages:

- Does not ingest PDFs or OCR-extracted bills.
- Does not reconstruct charges, riders, taxes, or demand calculations.
- Does not split non-calendar periods across reporting months yet; it preserves dates and flags proration need.
- Does not distinguish market-based and location-based Scope 2.

References consulted:

- Vista Power discussion of commercial electric bills, interval CSV downloads, tariff sheets, kWh bands, and demand charges.
- Utility-bill extraction articles describing common fields such as usage, charges, billing periods, and addresses.

## Corporate Travel

Researched:

- SAP Concur travel itinerary API behavior.
- Navan booking/travel API references and Airbyte connector notes.
- Travel booking categories and how they map to emission factors.

Real-world format studied:

- SAP Concur itinerary queries support date windows, user filters, and booking types such as Air, Car, Hotel, Rail, Ride, Parking, and Dining.
- Concur itinerary details contain booking segments where the shape differs by segment type.
- Navan booking APIs similarly expose trips/bookings for flights and hotels, but Concur was selected for the prototype.

Why the sample data is realistic:

- Contains one trip with flight, hotel, and ride segments.
- Uses traveler names, trip ids, airport codes, cities, nights, cabin/mode hints, and mixed date formats.
- Includes a failed airport-code route (`LHR` to `ZZZ`) to show distance lookup failure.

Limitations and breakages:

- Airport distance lookup is a tiny static table, not IATA-backed geodesic calculation.
- Does not handle cancellations, exchanges, multi-leg tickets, rail, parking, dining, or car rental fuel details.
- Does not apply cabin-class or radiative-forcing policy multipliers.
- Does not integrate with Concur OAuth or pagination.

References consulted:

- SAP Concur Developer Center, Travel itinerary API guide, including booking type filters such as Air, Car, Hotel, Rail, Ride, and Parking.
- Airbyte Navan connector notes describing booking data such as hotels and flights.
- Navan API references describing trip, booking, itinerary, invoice, and user profile access.