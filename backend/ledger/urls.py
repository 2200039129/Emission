from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("tenants/<slug:tenant_slug>/records/", views.records),
    path("tenants/<slug:tenant_slug>/ingestions/", views.ingest),
    path("records/<int:record_id>/approve/", views.approve),
    path("records/<int:record_id>/flag/", views.flag),
]