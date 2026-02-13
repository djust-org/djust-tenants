"""Tests for tenant resolvers."""

import pytest
from django.test import RequestFactory, override_settings

from djust_tenants.resolvers import (
    HeaderResolver,
    PathResolver,
    SessionResolver,
    SubdomainResolver,
    TenantInfo,
)

from .testapp.models import Organization


@pytest.fixture
def org(db):
    """Create test organization."""
    return Organization.objects.create(name="Acme Corp", slug="acme", is_active=True)


@pytest.fixture
def rf():
    """Request factory."""
    return RequestFactory()


class TestSubdomainResolver:
    """Tests for SubdomainResolver."""

    @override_settings(
        DJUST_TENANTS={
            "MAIN_DOMAIN": "example.com",
            "SUBDOMAIN_EXCLUDE": ["www", "api"],
        }
    )
    def test_resolve_subdomain(self, rf, org):
        """Test resolving tenant from subdomain."""
        resolver = SubdomainResolver()

        # Create request with subdomain
        request = rf.get("/")
        request.META["HTTP_HOST"] = "acme.example.com"

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.slug == "acme"
        assert tenant.name == "Acme Corp"
        assert tenant.obj == org

    @override_settings(DJUST_TENANTS={"MAIN_DOMAIN": "example.com"})
    def test_resolve_excluded_subdomain(self, rf):
        """Test that excluded subdomains return None."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "www.example.com"

        tenant = resolver.resolve(request)
        assert tenant is None

    def test_resolve_nonexistent_tenant(self, rf):
        """Test resolving non-existent tenant."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "nonexistent.example.com"

        tenant = resolver.resolve(request)
        assert tenant is None


class TestPathResolver:
    """Tests for PathResolver."""

    @override_settings(
        DJUST_TENANTS={
            "PATH_POSITION": 1,
            "PATH_EXCLUDE": ["admin", "api"],
        }
    )
    def test_resolve_path(self, rf, org):
        """Test resolving tenant from URL path."""
        resolver = PathResolver()

        request = rf.get("/acme/dashboard/")

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.slug == "acme"

    @override_settings(DJUST_TENANTS={"PATH_POSITION": 1})
    def test_resolve_excluded_path(self, rf):
        """Test that excluded paths return None."""
        resolver = PathResolver()

        request = rf.get("/admin/login/")

        tenant = resolver.resolve(request)
        assert tenant is None


class TestHeaderResolver:
    """Tests for HeaderResolver."""

    @override_settings(DJUST_TENANTS={"HEADER_NAME": "X-Tenant-ID"})
    def test_resolve_header(self, rf, org):
        """Test resolving tenant from HTTP header."""
        resolver = HeaderResolver()

        request = rf.get("/")
        request.META["HTTP_X_TENANT_ID"] = "acme"

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.slug == "acme"

    def test_resolve_missing_header(self, rf):
        """Test resolving when header is missing."""
        resolver = HeaderResolver()

        request = rf.get("/")

        tenant = resolver.resolve(request)
        assert tenant is None


class TestSessionResolver:
    """Tests for SessionResolver."""

    @override_settings(DJUST_TENANTS={"SESSION_KEY": "tenant_id"})
    def test_resolve_session(self, rf, org, db):
        """Test resolving tenant from session."""
        from django.contrib.sessions.middleware import SessionMiddleware

        resolver = SessionResolver()

        request = rf.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session["tenant_id"] = str(org.id)
        request.session.save()

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.slug == "acme"

    def test_resolve_missing_session(self, rf):
        """Test resolving when session key is missing."""
        from django.contrib.sessions.middleware import SessionMiddleware

        resolver = SessionResolver()

        request = rf.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()

        tenant = resolver.resolve(request)
        assert tenant is None
