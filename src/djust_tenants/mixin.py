"""
TenantMixin for djust LiveViews.

Provides automatic tenant resolution and tenant-scoped context for
multi-tenant SaaS applications.

``self.tenant`` is resolved before any user code runs, whether the view is
served over HTTP (``dispatch`` → ``get``/``post``) or over WebSocket
(``mount`` called directly by ``LiveViewConsumer``).

Example::

    from djust import LiveView
    from djust.tenants import TenantMixin

    class DashboardView(TenantMixin, LiveView):
        template_name = 'dashboard.html'

        def mount(self, request, **kwargs):
            # self.tenant is already set — works for both HTTP and WebSocket
            self.items = Item.objects.filter(tenant=self.tenant.id)

        def get_context_data(self):
            ctx = super().get_context_data()
            # tenant is automatically added to context
            # Access: {{ tenant.name }}, {{ tenant.settings.theme }}
            return ctx

Configuration::

    DJUST_TENANTS = {
        'RESOLVER': 'subdomain',  # or 'path', 'header', 'session', 'custom'
        'REQUIRED': True,  # Raise Http404 if no tenant found
        'CONTEXT_NAME': 'tenant',  # Name in template context
    }
"""

import logging
import warnings
from typing import TYPE_CHECKING, Any, Dict, Optional

from .resolvers import TenantInfo, resolve_tenant

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class TenantMixin:
    """
    Mixin that provides tenant awareness to LiveView classes.

    Features:
    - Auto-extracts tenant from request using configured resolver
    - Makes tenant available as self.tenant in all methods (HTTP and WebSocket)
    - Adds tenant to template context automatically
    - Provides tenant-scoped presence keys
    - Integrates with tenant-aware state backends

    Lifecycle hooks (resolution order):
    - mount()    — WebSocket/LiveView path; resolves tenant before the base
                   LiveView.mount() runs, so self.tenant is ready in mount().
    - dispatch() — HTTP path; resolves tenant before get()/post() handling.

    Both hooks call the same idempotent ``_ensure_tenant()``, so a view served
    over HTTP never resolves twice even if both hooks fire.

    Usage::

        class MyView(TenantMixin, LiveView):
            template_name = 'my_view.html'

            def mount(self, request, **kwargs):
                # self.tenant is already set — safe on both HTTP and WebSocket
                self.data = MyModel.objects.filter(tenant_id=self.tenant.id)

    Configuration options (DJUST_TENANTS setting):
    - RESOLVER: Resolution strategy ('subdomain', 'path', 'header', 'session', 'custom')
    - REQUIRED: If True, raises Http404 when tenant cannot be resolved
    - CONTEXT_NAME: Name used in template context (default: 'tenant')
    """

    # Class-level configuration
    tenant_required: bool = True  # Override per-view if needed
    tenant_context_name: str = "tenant"  # Name in template context

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tenant: Optional[TenantInfo] = None
        self._tenant_resolved: bool = False

    @property
    def tenant(self) -> Optional[TenantInfo]:
        """
        Get the current tenant.

        Returns:
            TenantInfo object or None if not resolved.

        Raises a UserWarning in DEBUG mode if accessed before mount() or
        dispatch() has run, so the silent-None bug surfaces immediately.
        """
        if not self._tenant_resolved:
            try:
                from django.conf import settings

                if getattr(settings, "DEBUG", False):
                    warnings.warn(
                        f"{self.__class__.__name__}.tenant accessed before resolution; "
                        "call mount() or dispatch() first.",
                        UserWarning,
                        stacklevel=2,
                    )
            except Exception:
                pass
        return self._tenant

    @tenant.setter
    def tenant(self, value: TenantInfo):
        """Set the tenant (usually done automatically)."""
        self._tenant = value
        self._tenant_resolved = True

    def resolve_tenant(self, request: "HttpRequest") -> Optional[TenantInfo]:
        """
        Resolve tenant from the request.

        Override this method to customize tenant resolution logic.

        Args:
            request: Django HttpRequest

        Returns:
            TenantInfo if resolved, None otherwise
        """
        return resolve_tenant(request)

    def _ensure_tenant(self, request: "HttpRequest") -> None:
        """
        Ensure tenant is resolved for this request.

        Idempotent — guarded by ``_tenant_resolved`` so it is safe to call
        from both mount() and dispatch() without double-resolving.
        """
        if self._tenant_resolved:
            return

        self._tenant = self.resolve_tenant(request)
        self._tenant_resolved = True

        if self._tenant:
            logger.debug("Tenant resolved: %s", self._tenant.id)
        elif self._is_tenant_required():
            from django.http import Http404

            raise Http404("Tenant not found")

    def _is_tenant_required(self) -> bool:
        """Check if tenant is required for this view."""
        # Check view-level setting first
        if hasattr(self, "tenant_required"):
            return self.tenant_required

        # Fall back to global config
        try:
            from django.conf import settings

            config = getattr(settings, "DJUST_CONFIG", {})
            return config.get("TENANT_REQUIRED", True)
        except Exception:
            logger.debug("Could not load DJUST_CONFIG for TENANT_REQUIRED, defaulting to True")
            return True

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add tenant to template context."""
        context = super().get_context_data(**kwargs) if hasattr(super(), "get_context_data") else {}

        # Get context name from config or class attribute
        context_name = self.tenant_context_name
        try:
            from django.conf import settings

            config = getattr(settings, "DJUST_CONFIG", {})
            context_name = config.get("TENANT_CONTEXT_NAME", context_name)
        except Exception:
            logger.debug("Could not load DJUST_CONFIG for TENANT_CONTEXT_NAME")

        context[context_name] = self._tenant
        return context

    def get_presence_key(self) -> str:
        """
        Override presence key to be tenant-scoped.

        If using PresenceMixin, this ensures presence is isolated per tenant.
        """
        base_key = (
            super().get_presence_key()
            if hasattr(super(), "get_presence_key")
            else self.__class__.__name__
        )

        if self._tenant:
            return f"tenant:{self._tenant.id}:{base_key}"
        return base_key

    def get_state_key_prefix(self) -> str:
        """
        Get prefix for state storage keys.

        Used by tenant-aware state backends to isolate state per tenant.
        """
        if self._tenant:
            return f"tenant:{self._tenant.id}"
        return ""

    # Hook into LiveView lifecycle — both paths call the same idempotent
    # _ensure_tenant(), so double-resolution is never an issue.
    def mount(self, request, **kwargs):
        """Resolve tenant before mount (WebSocket/LiveView path)."""
        self._ensure_tenant(request)
        return super().mount(request, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Resolve tenant before dispatching (HTTP path)."""
        self._ensure_tenant(request)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Resolve tenant before GET handling."""
        self._ensure_tenant(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Resolve tenant before POST handling."""
        self._ensure_tenant(request)
        return super().post(request, *args, **kwargs)


class TenantScopedMixin(TenantMixin):
    """
    Extended TenantMixin with automatic queryset scoping.

    Provides helper methods for common tenant-scoped operations.

    Usage::

        class ItemListView(TenantScopedMixin, LiveView):
            model = Item  # Your model with tenant_id field

            def mount(self, request, **kwargs):
                # Automatically scoped to current tenant
                self.items = self.get_tenant_queryset()
    """

    model = None  # Set this to your model class
    tenant_field: str = "tenant_id"  # Field name for tenant FK

    def get_tenant_queryset(self, model=None):
        """
        Get queryset filtered by current tenant.

        Args:
            model: Model class (defaults to self.model)

        Returns:
            QuerySet filtered by tenant
        """
        model = model or self.model
        if model is None:
            raise ValueError("No model specified for tenant-scoped queryset")

        if not self._tenant:
            logger.warning("Tenant not resolved, returning empty queryset")
            return model.objects.none()

        filter_kwargs = {self.tenant_field: self._tenant.id}
        return model.objects.filter(**filter_kwargs)

    def create_for_tenant(self, model=None, **kwargs):
        """
        Create a model instance with tenant automatically set.

        Args:
            model: Model class (defaults to self.model)
            **kwargs: Fields for the new instance

        Returns:
            Created model instance
        """
        model = model or self.model
        if model is None:
            raise ValueError("No model specified for tenant-scoped create")

        if not self._tenant:
            raise ValueError("Cannot create object: tenant not resolved")

        kwargs[self.tenant_field] = self._tenant.id
        return model.objects.create(**kwargs)

    def get_tenant_object(self, pk, model=None):
        """
        Get a specific object scoped to current tenant.

        Args:
            pk: Primary key of the object
            model: Model class (defaults to self.model)

        Returns:
            Model instance or raises DoesNotExist
        """
        model = model or self.model
        if model is None:
            raise ValueError("No model specified for tenant-scoped lookup")

        filter_kwargs = {
            "pk": pk,
            self.tenant_field: self._tenant.id if self._tenant else None,
        }
        return model.objects.get(**filter_kwargs)


class TenantContextProcessor:
    """
    Django context processor that adds tenant to all templates.

    Add to settings.py::

        TEMPLATES = [{
            'OPTIONS': {
                'context_processors': [
                    ...
                    'djust.tenants.context_processor',  # Add this
                ],
            },
        }]

    Then in templates::

        {{ tenant.name }}
        {{ tenant.settings.theme }}
    """

    def __call__(self, request):
        """Process request and return tenant context."""
        tenant = resolve_tenant(request)

        context_name = "tenant"
        try:
            from django.conf import settings

            config = getattr(settings, "DJUST_CONFIG", {})
            context_name = config.get("TENANT_CONTEXT_NAME", "tenant")
        except Exception:
            logger.debug("Could not load DJUST_CONFIG for TENANT_CONTEXT_NAME")

        return {context_name: tenant}


# Convenience function for use as context processor
def context_processor(request):
    """Context processor function that adds tenant to template context."""
    return TenantContextProcessor()(request)
