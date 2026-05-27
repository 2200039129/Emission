from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.slug


class SourceSystem(models.Model):
    SAP_FLAT_FILE = "sap_flat_file"
    UTILITY_CSV = "utility_csv"
    CONCUR_JSON = "concur_json"
    SOURCE_CHOICES = [
        (SAP_FLAT_FILE, "SAP MM flat file"),
        (UTILITY_CSV, "Utility CSV export"),
        (CONCUR_JSON, "SAP Concur itinerary JSON"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=40, choices=SOURCE_CHOICES)
    display_name = models.CharField(max_length=160)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("tenant", "source_type", "display_name")]


class IngestionBatch(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="batches")
    source = models.ForeignKey(SourceSystem, on_delete=models.PROTECT, related_name="batches")
    filename = models.CharField(max_length=240, blank=True)
    payload_sha256 = models.CharField(max_length=64)
    received_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=32, default="parsed")
    parser_version = models.CharField(max_length=32, default="2026-01-prototype")


class RawRecord(models.Model):
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="raw_records")
    row_number = models.PositiveIntegerField()
    external_id = models.CharField(max_length=160, blank=True)
    raw_payload = models.JSONField()
    parse_errors = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("batch", "row_number")]


class NormalizedRecord(models.Model):
    STATUS_CHOICES = [
        ("needs_review", "Needs review"),
        ("suspicious", "Suspicious"),
        ("failed", "Failed"),
        ("approved_locked", "Approved and locked"),
    ]
    SCOPE_CHOICES = [("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="records")
    raw_record = models.OneToOneField(RawRecord, on_delete=models.PROTECT, related_name="normalized")
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    activity_type = models.CharField(max_length=80)
    activity_label = models.CharField(max_length=240)
    facility_or_traveler = models.CharField(max_length=180)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    raw_quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    raw_unit = models.CharField(max_length=32, blank=True)
    normalized_quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    normalized_unit = models.CharField(max_length=32, blank=True)
    emission_factor_key = models.CharField(max_length=120, blank=True)
    emissions_kg_co2e = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="needs_review")
    issues = models.JSONField(default=list, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def approve_and_lock(self, user=None):
        if self.status == "failed":
            raise ValueError("Failed records must be corrected before approval.")
        self.status = "approved_locked"
        self.locked_at = timezone.now()
        if user and user.is_authenticated:
            self.locked_by = user
        self.save(update_fields=["status", "locked_at", "locked_by", "updated_at"])

    @property
    def is_locked(self):
        return self.locked_at is not None


class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_events")
    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name="audit_events", null=True, blank=True)
    actor = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class EmissionFactor(models.Model):
    key = models.CharField(max_length=120, unique=True)
    scope = models.CharField(max_length=16, choices=NormalizedRecord.SCOPE_CHOICES)
    activity_type = models.CharField(max_length=80)
    numerator_unit = models.CharField(max_length=32, default="kg_co2e")
    denominator_unit = models.CharField(max_length=32)
    factor = models.DecimalField(max_digits=18, decimal_places=8)
    source = models.CharField(max_length=240)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)