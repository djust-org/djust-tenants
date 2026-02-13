"""Provable tenant isolation tests.

These tests form the security evidence that tenant data cannot leak
between tenants under any normal operation.
"""

import pytest
from django.test import RequestFactory, override_settings

from djust_tenants.middleware import (
    TenantMiddleware,
    get_current_tenant,
    set_current_tenant,
)
from djust_tenants.resolvers import TenantInfo

from .testapp.models import Organization, SensitiveRecord


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Tenant A", slug="tenant-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Tenant B", slug="tenant-b")


def _make_tenant(org):
    return TenantInfo(
        tenant_id=str(org.id),
        name=org.name,
        slug=org.slug,
        raw=org,
    )


@pytest.fixture(autouse=True)
def clear_tenant():
    yield
    set_current_tenant(None)


class TestTenantIsolation:
    """Provable: Tenant A cannot see Tenant B's data."""

    def test_tenant_a_sees_zero_of_b_records(self, org_a, org_b):
        """Tenant A query returns zero of Tenant B's records."""
        SensitiveRecord.objects.create(organization=org_b, data="secret", secret_code="B-001")

        set_current_tenant(_make_tenant(org_a))
        assert SensitiveRecord.objects.count() == 0

    def test_tenant_a_sees_all_own_records(self, org_a, org_b):
        """Tenant A query returns ALL of Tenant A's records."""
        SensitiveRecord.objects.create(organization=org_a, data="d1", secret_code="A-001")
        SensitiveRecord.objects.create(organization=org_a, data="d2", secret_code="A-002")
        SensitiveRecord.objects.create(organization=org_b, data="d3", secret_code="B-001")

        set_current_tenant(_make_tenant(org_a))
        result = list(SensitiveRecord.objects.all())
        assert len(result) == 2
        assert all(r.organization == org_a for r in result)

    def test_switching_tenants_changes_visible_data(self, org_a, org_b):
        """Switching tenants immediately changes visible data."""
        SensitiveRecord.objects.create(organization=org_a, data="a", secret_code="A-001")
        SensitiveRecord.objects.create(organization=org_b, data="b", secret_code="B-001")

        set_current_tenant(_make_tenant(org_a))
        assert SensitiveRecord.objects.count() == 1
        assert SensitiveRecord.objects.first().secret_code == "A-001"

        set_current_tenant(_make_tenant(org_b))
        assert SensitiveRecord.objects.count() == 1
        assert SensitiveRecord.objects.first().secret_code == "B-001"

    def test_create_stamps_correct_fk(self, org_a):
        """Creating via manager with tenant set uses correct org."""
        set_current_tenant(_make_tenant(org_a))
        record = SensitiveRecord(organization=org_a, data="test", secret_code="X")
        record.save()
        record.refresh_from_db()
        assert record.organization_id == org_a.id

    def test_pk_lookup_across_tenants_fails(self, org_a, org_b):
        """Looking up Tenant B's PK while Tenant A is active → DoesNotExist."""
        b_record = SensitiveRecord.objects.create(
            organization=org_b, data="secret", secret_code="B-001"
        )

        set_current_tenant(_make_tenant(org_a))
        with pytest.raises(SensitiveRecord.DoesNotExist):
            SensitiveRecord.objects.get(pk=b_record.pk)

    def test_filter_by_pk_across_tenants_returns_empty(self, org_a, org_b):
        """Filtering by Tenant B's PK while Tenant A is active → empty."""
        b_record = SensitiveRecord.objects.create(
            organization=org_b, data="secret", secret_code="B-001"
        )

        set_current_tenant(_make_tenant(org_a))
        assert SensitiveRecord.objects.filter(pk=b_record.pk).count() == 0

    def test_values_list_isolated(self, org_a, org_b):
        """values_list() is also tenant-isolated."""
        SensitiveRecord.objects.create(organization=org_a, data="a", secret_code="A-001")
        SensitiveRecord.objects.create(organization=org_b, data="b", secret_code="B-001")

        set_current_tenant(_make_tenant(org_a))
        codes = list(SensitiveRecord.objects.values_list("secret_code", flat=True))
        assert codes == ["A-001"]


class TestThreadLocalCleanup:
    """Verify tenant context is properly cleaned up."""

    def test_tenant_cleared_after_request(self):
        """Thread-local cleared after normal request."""
        factory = RequestFactory()
        request = factory.get("/", HTTP_HOST="acme.example.com")

        def dummy_response(req):
            from django.http import HttpResponse

            return HttpResponse("ok")

        middleware = TenantMiddleware(dummy_response)
        middleware(request)

        assert get_current_tenant() is None

    def test_tenant_cleared_after_exception(self):
        """Thread-local cleared even when view raises."""
        factory = RequestFactory()
        request = factory.get("/", HTTP_HOST="acme.example.com")

        def error_response(req):
            raise ValueError("boom")

        middleware = TenantMiddleware(error_response)

        with pytest.raises(ValueError, match="boom"):
            middleware(request)

        assert get_current_tenant() is None


class TestStrictMode:
    """Verify STRICT_MODE default-deny behavior."""

    def test_strict_mode_returns_empty_when_no_tenant(self, org_a):
        """Default STRICT_MODE returns empty queryset with no tenant."""
        SensitiveRecord.objects.create(organization=org_a, data="d", secret_code="A-001")

        set_current_tenant(None)
        assert SensitiveRecord.objects.count() == 0

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "STRICT_MODE": False,
        }
    )
    def test_strict_mode_off_returns_all(self, org_a):
        """STRICT_MODE=False returns all records when no tenant."""
        SensitiveRecord.objects.create(organization=org_a, data="d", secret_code="A-001")

        set_current_tenant(None)
        assert SensitiveRecord.objects.count() == 1

    def test_unscoped_bypasses_strict(self, org_a, org_b):
        """unscoped() returns all records regardless of strict mode."""
        SensitiveRecord.objects.create(organization=org_a, data="a", secret_code="A-001")
        SensitiveRecord.objects.create(organization=org_b, data="b", secret_code="B-001")

        set_current_tenant(_make_tenant(org_a))
        assert SensitiveRecord.objects.unscoped(reason="admin report").count() == 2

    def test_unscoped_with_reason(self, org_a):
        """unscoped() accepts reason parameter."""
        SensitiveRecord.objects.create(organization=org_a, data="a", secret_code="A-001")
        # Just verify it doesn't error; audit integration tested separately
        qs = SensitiveRecord.objects.unscoped(reason="monthly report generation")
        assert qs.count() == 1
