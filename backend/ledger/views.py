from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AuditEvent, NormalizedRecord, Tenant
from .serializers import IngestionRequestSerializer, NormalizedRecordSerializer
from .services import ingest_payload


@api_view(["GET"])
def health(_request):
    return Response({"ok": True, "service": "carbon-ledger-api"})


@api_view(["GET"])
def records(request, tenant_slug):
    tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_slug.replace("-", " ").title()})
    queryset = NormalizedRecord.objects.filter(tenant=tenant).select_related("raw_record__batch__source").order_by("-created_at")
    status_filter = request.query_params.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return Response(NormalizedRecordSerializer(queryset, many=True).data)


@api_view(["POST"])
def ingest(request, tenant_slug):
    serializer = IngestionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    batch, records_created = ingest_payload(tenant_slug=tenant_slug, **serializer.validated_data)
    return Response(
        {
            "batch_id": batch.id,
            "created": len(records_created),
            "records": NormalizedRecordSerializer(records_created, many=True).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def approve(request, record_id):
    record = NormalizedRecord.objects.select_related("tenant").get(id=record_id)
    before = {"status": record.status, "locked_at": str(record.locked_at)}
    try:
        record.approve_and_lock(request.user)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    AuditEvent.objects.create(
        tenant=record.tenant,
        record=record,
        actor=request.user if request.user.is_authenticated else None,
        action="approve_and_lock",
        before=before,
        after={"status": record.status, "locked_at": str(record.locked_at)},
        reason=request.data.get("reason", "Analyst approval"),
    )
    return Response(NormalizedRecordSerializer(record).data)


@api_view(["POST"])
def flag(request, record_id):
    record = NormalizedRecord.objects.select_related("tenant").get(id=record_id)
    if record.is_locked:
        return Response({"detail": "Approved records are locked. Create a reversal batch instead."}, status=status.HTTP_409_CONFLICT)
    before = {"status": record.status, "issues": record.issues}
    issue = request.data.get("issue", "Manually flagged by analyst")
    record.issues = sorted(set([*record.issues, issue]))
    record.status = "suspicious"
    record.save(update_fields=["issues", "status", "updated_at"])
    AuditEvent.objects.create(
        tenant=record.tenant,
        record=record,
        actor=request.user if request.user.is_authenticated else None,
        action="flag_suspicious",
        before=before,
        after={"status": record.status, "issues": record.issues},
        reason=issue,
    )
    return Response(NormalizedRecordSerializer(record).data)