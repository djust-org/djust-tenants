"""Tests for TenantMiddleware."""

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from djust_tenants.middleware import TenantMiddleware, get_current_tenant, set_current_tenant


@pytest.fixture
def rf():
    """Request factory."""
    return RequestFactory()


class TestTenantMiddleware:
    """Tests for TenantMiddleware."""

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "REQUIRED": False,
        }
    )
    def test_middleware_sets_tenant(self, rf):
        """Test that middleware sets request.tenant."""

        def get_response(request):
            # Check tenant is set on request
            assert hasattr(request, "tenant")
            assert request.tenant is not None
            assert request.tenant.id == "acme"
            assert request.tenant.slug == "acme"

            # Check thread-local tenant is set
            current_tenant = get_current_tenant()
            assert current_tenant is not None
            assert current_tenant.id == "acme"

            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantMiddleware(get_response)

        request = rf.get("/")
        request.META["HTTP_HOST"] = "acme.example.com"

        response = middleware(request)

        assert response.status_code == 200

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "REQUIRED": False,
        }
    )
    def test_middleware_clears_thread_local(self, rf):
        """Test that middleware clears thread-local after request."""

        def get_response(request):
            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantMiddleware(get_response)

        request = rf.get("/")
        request.META["HTTP_HOST"] = "acme.example.com"

        middleware(request)

        # Thread-local should be cleared after request
        assert get_current_tenant() is None

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "REQUIRED": True,  # Tenant required
        }
    )
    def test_middleware_raises_404_when_required(self, rf):
        """Test that middleware raises 404 when tenant required but not found."""

        def get_response(request):
            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantMiddleware(get_response)

        request = rf.get("/")
        request.META["HTTP_HOST"] = "www.example.com"  # Excluded subdomain

        with pytest.raises(Http404, match="Tenant not found"):
            middleware(request)

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "REQUIRED": False,
        }
    )
    def test_middleware_allows_no_tenant(self, rf):
        """Test that middleware allows no tenant when not required."""

        def get_response(request):
            assert hasattr(request, "tenant")
            assert request.tenant is None

            from django.http import HttpResponse

            return HttpResponse("OK")

        middleware = TenantMiddleware(get_response)

        request = rf.get("/")
        request.META["HTTP_HOST"] = "www.example.com"  # Excluded subdomain

        response = middleware(request)
        assert response.status_code == 200


class TestThreadLocalHelpers:
    """Tests for get_current_tenant / set_current_tenant."""

    def test_set_and_get(self):
        """Test basic set/get cycle."""
        from djust_tenants.resolvers import TenantInfo

        tenant = TenantInfo(tenant_id="test")
        set_current_tenant(tenant)
        assert get_current_tenant() == tenant
        set_current_tenant(None)
        assert get_current_tenant() is None

    def test_default_is_none(self):
        """Test that default tenant is None."""
        set_current_tenant(None)  # ensure clean state
        assert get_current_tenant() is None
