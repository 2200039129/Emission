from rest_framework import serializers

from .models import IngestionBatch, NormalizedRecord


class IngestionRequestSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=["sap_flat_file", "utility_csv", "concur_json"])
    payload = serializers.CharField()
    filename = serializers.CharField(required=False, allow_blank=True)


class NormalizedRecordSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(source="raw_record.batch.source.source_type")
    batch_id = serializers.IntegerField(source="raw_record.batch_id")
    raw_payload = serializers.JSONField(source="raw_record.raw_payload")
    locked = serializers.BooleanField(source="is_locked")

    class Meta:
        model = NormalizedRecord
        fields = [
            "id",
            "batch_id",
            "source_type",
            "scope",
            "activity_type",
            "activity_label",
            "facility_or_traveler",
            "period_start",
            "period_end",
            "raw_quantity",
            "raw_unit",
            "normalized_quantity",
            "normalized_unit",
            "emission_factor_key",
            "emissions_kg_co2e",
            "status",
            "issues",
            "locked",
            "locked_at",
            "raw_payload",
        ]


class IngestionBatchSerializer(serializers.ModelSerializer):
    record_count = serializers.IntegerField(source="raw_records.count", read_only=True)

    class Meta:
        model = IngestionBatch
        fields = ["id", "filename", "payload_sha256", "received_at", "status", "parser_version", "record_count"]