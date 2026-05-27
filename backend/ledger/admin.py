from django.contrib import admin

from .models import AuditEvent, EmissionFactor, IngestionBatch, NormalizedRecord, RawRecord, SourceSystem, Tenant


admin.site.register([Tenant, SourceSystem, IngestionBatch, RawRecord, NormalizedRecord, AuditEvent, EmissionFactor])