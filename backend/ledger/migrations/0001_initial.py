# Generated for the carbon ledger prototype.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="EmissionFactor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=120, unique=True)),
                ("scope", models.CharField(choices=[("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")], max_length=16)),
                ("activity_type", models.CharField(max_length=80)),
                ("numerator_unit", models.CharField(default="kg_co2e", max_length=32)),
                ("denominator_unit", models.CharField(max_length=32)),
                ("factor", models.DecimalField(decimal_places=8, max_digits=18)),
                ("source", models.CharField(max_length=240)),
                ("valid_from", models.DateField()),
                ("valid_to", models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="SourceSystem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("sap_flat_file", "SAP MM flat file"), ("utility_csv", "Utility CSV export"), ("concur_json", "SAP Concur itinerary JSON")], max_length=40)),
                ("display_name", models.CharField(max_length=160)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sources", to="ledger.tenant")),
            ],
            options={"unique_together": {("tenant", "source_type", "display_name")}},
        ),
        migrations.CreateModel(
            name="IngestionBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(blank=True, max_length=240)),
                ("payload_sha256", models.CharField(max_length=64)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("status", models.CharField(default="parsed", max_length=32)),
                ("parser_version", models.CharField(default="2026-01-prototype", max_length=32)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="batches", to="ledger.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batches", to="ledger.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="RawRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row_number", models.PositiveIntegerField()),
                ("external_id", models.CharField(blank=True, max_length=160)),
                ("raw_payload", models.JSONField()),
                ("parse_errors", models.JSONField(blank=True, default=list)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ledger.ingestionbatch")),
            ],
            options={"unique_together": {("batch", "row_number")}},
        ),
        migrations.CreateModel(
            name="NormalizedRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")], max_length=16)),
                ("activity_type", models.CharField(max_length=80)),
                ("activity_label", models.CharField(max_length=240)),
                ("facility_or_traveler", models.CharField(max_length=180)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("raw_quantity", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("raw_unit", models.CharField(blank=True, max_length=32)),
                ("normalized_quantity", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("normalized_unit", models.CharField(blank=True, max_length=32)),
                ("emission_factor_key", models.CharField(blank=True, max_length=120)),
                ("emissions_kg_co2e", models.DecimalField(decimal_places=6, default=0, max_digits=18)),
                ("status", models.CharField(choices=[("needs_review", "Needs review"), ("suspicious", "Suspicious"), ("failed", "Failed"), ("approved_locked", "Approved and locked")], default="needs_review", max_length=32)),
                ("issues", models.JSONField(blank=True, default=list)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("locked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("raw_record", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="normalized", to="ledger.rawrecord")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="ledger.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=80)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ledger.normalizedrecord")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ledger.tenant")),
            ],
        ),
    ]