"""Tests for TenantMixin — covering both HTTP and WebSocket (mount) paths."""

import warnings

import pytest
from django.test import RequestFactory, override_settings

from djust_tenants.mixin import TenantMixin
from djust_tenants.resolvers import TenantInfo


# ---------------------------------------------------------------------------
# Minimal stub LiveView so we can test the mixin without the full djust stack
# ---------------------------------------------------------------------------


class _BaseView:
    """Minimal stand-in for djust's LiveView base class."""

    def mount(self, request, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        pass

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass


class _TenantView(TenantMixin, _BaseView):
    """A view that uses TenantMixin (tenant required — raises Http404 if not resolved)."""

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        # Record what self.tenant was when mount() ran
        self.tenant_at_mount = self.tenant


class _OptionalTenantView(TenantMixin, _BaseView):
    """A view that uses TenantMixin with tenant_required=False."""

    tenant_required = False

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self.tenant_at_mount = self.tenant


# ---------------------------------------------------------------------------
# Settings that inject a predictable tenant via a custom resolver
# ---------------------------------------------------------------------------

_TENANT_SETTINGS = {
    "RESOLVER": "custom",
    "CUSTOM_RESOLVER": "tests.test_mixin._always_acme_resolver",
}


def _always_acme_resolver(request):
    """Custom resolver that always returns a fixed tenant — for testing."""
    return TenantInfo(
        tenant_id="acme",
        name="Acme Corp",
        slug="acme",
        raw=None,
    )


@pytest.fixture
def rf():
    return RequestFactory()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTenantMixinMountPath:
    """Verify that self.tenant is resolved when mount() is called directly.

    This simulates the djust WebSocket consumer path, which calls
    view_instance.mount(request) without going through dispatch/get/post.
    """

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_resolved_when_mount_called_directly(self, rf):
        """Tenant must be set after mount() — simulates WebSocket path."""
        view = _TenantView()
        request = rf.get("/")
        view.mount(request)

        assert view.tenant is not None, (
            "self.tenant is None after mount() — TenantMixin.mount() override is missing"
        )
        assert view.tenant.id == "acme"

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_available_inside_mount_body(self, rf):
        """self.tenant should be set before the subclass mount() body runs."""
        view = _TenantView()
        request = rf.get("/")
        view.mount(request)

        assert view.tenant_at_mount is not None
        assert view.tenant_at_mount.id == "acme"

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_mount_is_idempotent(self, rf):
        """Calling mount() twice should not raise or reset the tenant."""
        view = _TenantView()
        request = rf.get("/")
        view.mount(request)
        view.mount(request)  # second call should be a no-op

        assert view.tenant is not None
        assert view.tenant.id == "acme"

    @override_settings(
        DJUST_TENANTS={"RESOLVER": "subdomain", "MAIN_DOMAIN": "example.com", "REQUIRED": False}
    )
    def test_tenant_none_when_no_resolver_match(self, rf):
        """When no tenant is resolved and tenant_required=False, self.tenant is None (no raise)."""
        view = _OptionalTenantView()
        request = rf.get("/")
        request.META["HTTP_HOST"] = "example.com"  # main domain → no subdomain tenant
        view.mount(request)

        assert view.tenant is None

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_persists_across_method_calls(self, rf):
        """Tenant resolved in mount() is still available in subsequent event handler calls.

        This simulates the real WebSocket flow: mount() runs once, then event
        handlers are invoked as separate method calls on the same view instance.
        The tenant must not require re-resolution on each call.
        """
        view = _TenantView()
        request = rf.get("/")
        view.mount(request)

        # Simulate an event handler accessing self.tenant after mount
        assert view.tenant is not None
        assert view.tenant.id == "acme"
        assert view._tenant_resolved is True

        # Access again — should return same object, not re-resolve
        first = view.tenant
        second = view.tenant
        assert first is second


class TestTenantMixinHttpPath:
    """Verify that self.tenant is still resolved in the HTTP dispatch path."""

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_resolved_via_dispatch(self, rf):
        view = _TenantView()
        request = rf.get("/")
        view.dispatch(request)
        assert view.tenant is not None
        assert view.tenant.id == "acme"

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_resolved_via_get(self, rf):
        view = _TenantView()
        request = rf.get("/")
        view.get(request)
        assert view.tenant is not None

    @override_settings(DJUST_TENANTS=_TENANT_SETTINGS)
    def test_tenant_resolved_via_post(self, rf):
        view = _TenantView()
        request = rf.post("/")
        view.post(request)
        assert view.tenant is not None


class TestTenantMixinDebugWarning:
    """Verify that accessing self.tenant before resolution warns in DEBUG mode."""

    @override_settings(DEBUG=True)
    def test_warns_in_debug_mode_before_resolution(self):
        view = _TenantView()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = view.tenant  # access before _ensure_tenant is called

        assert len(caught) == 1
        assert "_ensure_tenant" in str(caught[0].message)

    @override_settings(DEBUG=False)
    def test_no_warning_in_production(self):
        view = _TenantView()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = view.tenant

        assert len(caught) == 0

    @override_settings(DEBUG=True, DJUST_TENANTS=_TENANT_SETTINGS)
    def test_no_warning_after_resolution(self, rf):
        view = _TenantView()
        request = rf.get("/")
        view.mount(request)  # resolves tenant

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = view.tenant

        assert len(caught) == 0
