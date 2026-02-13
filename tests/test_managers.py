"""Tests for TenantManager."""

import pytest
from django.test import override_settings

from djust_tenants.middleware import set_current_tenant
from djust_tenants.resolvers import TenantInfo

from .testapp.models import Organization, Project


@pytest.fixture
def org1(db):
    """Create first test organization."""
    return Organization.objects.create(name="Acme Corp", slug="acme")


@pytest.fixture
def org2(db):
    """Create second test organization."""
    return Organization.objects.create(name="Startup Inc", slug="startup")


@pytest.fixture
def projects(org1, org2):
    """Create test projects for both orgs."""
    p1 = Project.objects.create(organization=org1, name="Project A")
    p2 = Project.objects.create(organization=org1, name="Project B")
    p3 = Project.objects.create(organization=org2, name="Project C")

    return (p1, p2, p3)


@pytest.fixture(autouse=True)
def clear_tenant():
    """Ensure tenant is cleared after each test."""
    yield
    set_current_tenant(None)


class TestTenantManager:
    """Tests for TenantManager."""

    def test_auto_filter_by_tenant(self, projects):
        """Test that queries are auto-filtered by current tenant."""
        p1, p2, p3 = projects

        # Set current tenant to org1
        tenant = TenantInfo(
            tenant_id=str(p1.organization.id),
            name=p1.organization.name,
            slug=p1.organization.slug,
            raw=p1.organization,
        )
        set_current_tenant(tenant)

        # Should only see org1's projects
        result = list(Project.objects.all())
        assert len(result) == 2
        assert p1 in result
        assert p2 in result
        assert p3 not in result

    def test_auto_filter_switches_with_tenant(self, projects):
        """Test that filter changes when tenant changes."""
        p1, p2, p3 = projects

        # Set to org1
        tenant1 = TenantInfo(
            tenant_id=str(p1.organization.id),
            name=p1.organization.name,
            slug=p1.organization.slug,
            raw=p1.organization,
        )
        set_current_tenant(tenant1)

        assert Project.objects.count() == 2

        # Switch to org2
        tenant2 = TenantInfo(
            tenant_id=str(p3.organization.id),
            name=p3.organization.name,
            slug=p3.organization.slug,
            raw=p3.organization,
        )
        set_current_tenant(tenant2)

        assert Project.objects.count() == 1

    def test_unscoped_bypasses_filter(self, projects):
        """Test that unscoped() bypasses tenant filtering."""
        p1, p2, p3 = projects

        # Set current tenant
        tenant = TenantInfo(
            tenant_id=str(p1.organization.id),
            name=p1.organization.name,
            slug=p1.organization.slug,
            raw=p1.organization,
        )
        set_current_tenant(tenant)

        # Normal query: filtered
        assert Project.objects.count() == 2

        # Unscoped: see all
        assert Project.objects.unscoped().count() == 3

    def test_no_tenant_returns_all(self, projects):
        """Test that no tenant returns all objects."""
        # No tenant set
        set_current_tenant(None)

        # Should see all projects
        assert Project.objects.count() == 3
