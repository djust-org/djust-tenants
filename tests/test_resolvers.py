"""Tests for tenant resolvers."""

import pytest
from django.test import RequestFactory, override_settings

from djust_tenants.resolvers import (
    ChainedResolver,
    HeaderResolver,
    PathResolver,
    SessionResolver,
    SubdomainResolver,
    TenantInfo,
)


@pytest.fixture
def rf():
    """Request factory."""
    return RequestFactory()


class TestTenantInfo:
    """Tests for TenantInfo dataclass."""

    def test_basic_creation(self):
        """Test creating TenantInfo with just an ID."""
        tenant = TenantInfo(tenant_id="acme")
        assert tenant.id == "acme"
        assert tenant.name == "acme"  # defaults to tenant_id
        assert tenant.slug == "acme"  # defaults to tenant_id
        assert tenant.obj is None
        assert tenant.raw is None

    def test_full_creation(self):
        """Test creating TenantInfo with all fields."""
        obj = {"some": "model"}
        tenant = TenantInfo(
            tenant_id="acme",
            name="Acme Corp",
            slug="acme-corp",
            settings={"theme": "dark"},
            metadata={"plan": "enterprise"},
            raw=obj,
        )
        assert tenant.id == "acme"
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.obj is obj
        assert tenant.raw is obj
        assert tenant.get_setting("theme") == "dark"

    def test_equality(self):
        """Test TenantInfo equality by ID."""
        t1 = TenantInfo(tenant_id="acme")
        t2 = TenantInfo(tenant_id="acme", name="Different Name")
        t3 = TenantInfo(tenant_id="other")
        assert t1 == t2
        assert t1 != t3
        assert t1 == "acme"

    def test_hash(self):
        """Test TenantInfo is hashable."""
        t1 = TenantInfo(tenant_id="acme")
        t2 = TenantInfo(tenant_id="acme")
        assert hash(t1) == hash(t2)
        assert len({t1, t2}) == 1


class TestSubdomainResolver:
    """Tests for SubdomainResolver."""

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "SUBDOMAIN_EXCLUDE": ["www", "api"],
        }
    )
    def test_resolve_subdomain(self, rf):
        """Test resolving tenant from subdomain."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "acme.example.com"

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"
        assert tenant.slug == "acme"

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
            "SUBDOMAIN_EXCLUDE": ["www", "api"],
        }
    )
    def test_resolve_excluded_subdomain(self, rf):
        """Test that excluded subdomains return None."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "www.example.com"

        tenant = resolver.resolve(request)
        assert tenant is None

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
            "MAIN_DOMAIN": "example.com",
        }
    )
    def test_resolve_no_subdomain(self, rf):
        """Test resolving when no subdomain is present."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "example.com"

        tenant = resolver.resolve(request)
        assert tenant is None

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "subdomain",
        }
    )
    def test_resolve_three_part_host(self, rf):
        """Test resolving from three-part hostname without MAIN_DOMAIN."""
        resolver = SubdomainResolver()

        request = rf.get("/")
        request.META["HTTP_HOST"] = "acme.example.com"

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"


class TestPathResolver:
    """Tests for PathResolver."""

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "path",
            "PATH_POSITION": 1,
            "PATH_EXCLUDE": ["admin", "api"],
        }
    )
    def test_resolve_path(self, rf):
        """Test resolving tenant from URL path."""
        resolver = PathResolver()

        request = rf.get("/acme/dashboard/")

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"
        assert tenant.slug == "acme"

    @override_settings(
        DJUST_TENANTS={
            "RESOLVER": "path",
            "PATH_POSITION": 1,
            "PATH_EXCLUDE": ["admin", "api"],
        }
    )
    def test_resolve_excluded_path(self, rf):
        """Test that excluded paths return None."""
        resolver = PathResolver()

        request = rf.get("/admin/login/")

        tenant = resolver.resolve(request)
        assert tenant is None

    @override_settings(DJUST_TENANTS={"RESOLVER": "path"})
    def test_resolve_empty_path(self, rf):
        """Test resolving from empty path."""
        resolver = PathResolver()

        request = rf.get("/")

        tenant = resolver.resolve(request)
        assert tenant is None


class TestHeaderResolver:
    """Tests for HeaderResolver."""

    @override_settings(DJUST_TENANTS={"RESOLVER": "header", "HEADER_NAME": "X-Tenant-ID"})
    def test_resolve_header(self, rf):
        """Test resolving tenant from HTTP header."""
        resolver = HeaderResolver()

        request = rf.get("/")
        request.META["HTTP_X_TENANT_ID"] = "acme"

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"
        assert tenant.slug == "acme"

    def test_resolve_missing_header(self, rf):
        """Test resolving when header is missing."""
        resolver = HeaderResolver()

        request = rf.get("/")

        tenant = resolver.resolve(request)
        assert tenant is None


class TestSessionResolver:
    """Tests for SessionResolver."""

    @pytest.mark.django_db
    @override_settings(DJUST_TENANTS={"RESOLVER": "session", "SESSION_KEY": "tenant_id"})
    def test_resolve_session(self, rf):
        """Test resolving tenant from session."""
        from django.contrib.sessions.middleware import SessionMiddleware

        resolver = SessionResolver()

        request = rf.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session["tenant_id"] = "acme"
        request.session.save()

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"

    @pytest.mark.django_db
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

    def test_resolve_from_user_attribute(self, rf):
        """Test resolving from user.tenant_id attribute."""
        resolver = SessionResolver()

        request = rf.get("/")

        # Mock user with tenant_id attribute
        class MockUser:
            tenant_id = "acme"

        request.user = MockUser()

        tenant = resolver.resolve(request)

        assert tenant is not None
        assert tenant.id == "acme"


class TestChainedResolver:
    """Tests for ChainedResolver."""

    @override_settings(DJUST_TENANTS={"HEADER_NAME": "X-Tenant-ID"})
    def test_chained_first_match_wins(self, rf):
        """Test that chained resolver returns first match."""
        resolver = ChainedResolver([HeaderResolver(), PathResolver()])

        request = rf.get("/other/dashboard/")
        request.META["HTTP_X_TENANT_ID"] = "acme"

        tenant = resolver.resolve(request)
        assert tenant is not None
        assert tenant.id == "acme"

    def test_chained_fallback(self, rf):
        """Test that chained resolver falls through to next resolver."""
        resolver = ChainedResolver([HeaderResolver(), PathResolver()])

        request = rf.get("/acme/dashboard/")

        tenant = resolver.resolve(request)
        assert tenant is not None
        assert tenant.id == "acme"

    def test_chained_no_match(self, rf):
        """Test that chained resolver returns None when no match."""
        resolver = ChainedResolver([HeaderResolver()])

        request = rf.get("/")

        tenant = resolver.resolve(request)
        assert tenant is None
