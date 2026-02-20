"""Tests for TenantMixin — WebSocket (mount) and HTTP dispatch paths."""

import warnings

import pytest
from django.test import RequestFactory, override_settings

from djust_tenants.mixin import TenantMixin
from djust_tenants.resolvers import TenantInfo

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------


class _FakeBase:
    """Minimal base simulating a LiveView without importing djust."""

    def mount(self, request, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        pass

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def get_context_data(self, **kwargs):
        return {}


class _AcmeView(TenantMixin, _FakeBase):
    """Always resolves to the 'acme' tenant; tenant not required."""

    tenant_required = False

    def resolve_tenant(self, request):
        return TenantInfo("acme")


class _NoTenantView(TenantMixin, _FakeBase):
    """Never resolves a tenant; tenant not required."""

    tenant_required = False

    def resolve_tenant(self, request):
        return None


@pytest.fixture
def rf():
    return RequestFactory()


# ---------------------------------------------------------------------------
# WebSocket / mount() path
# ---------------------------------------------------------------------------


class TestMountPath:
    def test_mount_resolves_tenant(self, rf):
        """Tenant is resolved when mount() is called directly (WebSocket path)."""
        view = _AcmeView()
        view.mount(rf.get("/"))
        assert view.tenant is not None
        assert view.tenant.id == "acme"

    def test_tenant_available_before_super_mount(self, rf):
        """_ensure_tenant() runs before super().mount() so base sees resolved tenant."""
        captured = []

        class _CaptureFakeBase(_FakeBase):
            def mount(self, request, **kwargs):
                # At this point TenantMixin.mount() has already called _ensure_tenant
                captured.append(self._tenant)

        class _CheckView(TenantMixin, _CaptureFakeBase):
            tenant_required = False

            def resolve_tenant(self, request):
                return TenantInfo("acme")

        view = _CheckView()
        view.mount(rf.get("/"))
        assert len(captured) == 1
        assert captured[0] is not None
        assert captured[0].id == "acme"

    def test_mount_idempotent(self, rf):
        """Calling mount() twice does not raise or reset the resolved tenant."""
        view = _AcmeView()
        request = rf.get("/")
        view.mount(request)
        first = view.tenant
        view.mount(request)  # second call must be a no-op
        assert view.tenant is first

    def test_no_tenant_when_resolver_returns_none(self, rf):
        """tenant is None when resolver finds no match and tenant_required=False."""
        view = _NoTenantView()
        view.mount(rf.get("/"))
        assert view.tenant is None

    def test_tenant_persists_across_event_handlers(self, rf):
        """Tenant set during mount() remains available for subsequent calls."""
        view = _AcmeView()
        view.mount(rf.get("/"))
        # Simulate an event handler reading self.tenant multiple times
        assert view.tenant is not None
        assert view.tenant.id == "acme"
        assert view.tenant is view.tenant  # stable reference


# ---------------------------------------------------------------------------
# HTTP dispatch / get / post paths (existing behaviour preserved)
# ---------------------------------------------------------------------------


class TestHTTPPath:
    def test_dispatch_resolves_tenant(self, rf):
        view = _AcmeView()
        view.dispatch(rf.get("/"))
        assert view.tenant is not None
        assert view.tenant.id == "acme"

    def test_get_resolves_tenant(self, rf):
        view = _AcmeView()
        view.get(rf.get("/"))
        assert view.tenant is not None
        assert view.tenant.id == "acme"

    def test_post_resolves_tenant(self, rf):
        view = _AcmeView()
        view.post(rf.post("/"))
        assert view.tenant is not None
        assert view.tenant.id == "acme"


# ---------------------------------------------------------------------------
# Debug warning on the tenant property
# ---------------------------------------------------------------------------


class TestTenantPropertyWarning:
    @override_settings(DEBUG=True)
    def test_warning_fires_before_resolution(self):
        """UserWarning is emitted when tenant is accessed before mount/dispatch."""
        view = _AcmeView()
        with pytest.warns(UserWarning, match="before resolution"):
            _ = view.tenant

    @override_settings(DEBUG=True)
    def test_no_warning_after_resolution(self, rf):
        """No warning after mount() has successfully resolved the tenant."""
        view = _AcmeView()
        view.mount(rf.get("/"))
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            _ = view.tenant  # must not raise

    @override_settings(DEBUG=False)
    def test_no_warning_in_production(self):
        """No warning emitted in production (DEBUG=False), even before resolution."""
        view = _AcmeView()
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            _ = view.tenant  # must not raise
