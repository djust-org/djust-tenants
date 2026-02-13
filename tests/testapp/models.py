"""Test models for djust-tenants."""

from django.db import models

from djust_tenants.managers import TenantManager


class Organization(models.Model):
    """Test tenant/organization model."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    """Test model with tenant FK."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=200)

    # Use TenantManager for auto-filtering
    objects = TenantManager(tenant_field="organization")

    def __str__(self):
        return f"{self.organization.name} / {self.name}"
