# Tradeoffs

## 1. No Direct Enterprise Connectors

I did not build live SAP OData, BAPI/RFC, Concur OAuth, Navan OAuth, or utility API pulls.

Why:

- The evaluation focus is data modeling and engineering judgment.
- Real connectors require customer credentials, sandbox tenants, network allowlists, and vendor-specific auth details.
- Manual paste/file ingestion still exercises the hard parts: parsing, normalization, source tracking, review, suspicious rows, and locks.

## 2. No Full Emission Factor Engine

I did not build a production factor engine with geography, validity windows, gas breakdowns, uncertainty, supplier instruments, cabin class multipliers, or market/location-based Scope 2 dual reporting.

Why:

- The model includes `EmissionFactor` and `emission_factor_key`, so the architecture can support it.
- Implementing a factor library would add volume without proving ingestion judgment.
- Prototype factors are enough to demonstrate different categories and units.

## 3. No Complex Approval Workflow

I did not build maker/checker, comments, task assignment, SSO, RBAC, or unlock-by-admin.

Why:

- The critical invariant is that approval creates an immutable audit lock.
- Multi-step workflow is product-specific and should be designed after PM clarification.
- The `AuditEvent` table and locked-row rule provide the foundation for a later workflow.