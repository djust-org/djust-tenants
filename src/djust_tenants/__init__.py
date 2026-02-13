"""
djust.tenants — Multi-tenant support for djust LiveViews.

Enables building SaaS applications with tenant isolation:
- Automatic tenant resolution from request (subdomain, path, header, session)
- Tenant-scoped state and presence backends
- Tenant context in templates

Quick Start::

    from djust import LiveView
    from djust.tenants import TenantMixin

    class DashboardView(TenantMixin, LiveView):
        template_name = 'dashboard.html'

        def mount(self, request, **kwargs):
            # self.tenant is automatically set from request
            self.items = Item.objects.filter(tenant=self.tenant.id)

Configuration in settings.py::

    DJUST_TENANTS = {
        # Tenant resolution strategy
        'RESOLVER': 'subdomain',  # 'subdomain', 'path', 'header', 'session', 'custom'

        # Subdomain options
        'SUBDOMAIN_EXCLUDE': ['www', 'api', 'admin'],
        'MAIN_DOMAIN': 'example.com',

        # Path options (example.com/acme/dashboard)
        'PATH_POSITION': 1,
        'PATH_EXCLUDE': ['admin', 'api', 'static'],

        # Header option (X-Tenant-ID header)
        'HEADER_NAME': 'X-Tenant-ID',

        # Session option
        'SESSION_KEY': 'tenant_id',

        # Custom resolver (dotted path to callable)
        'CUSTOM_RESOLVER': 'myapp.tenants.resolve_tenant',

        # Behavior options
        'REQUIRED': True,  # Raise 404 if no tenant found
        'DEFAULT_TENANT': None,  # Default tenant if none resolved
        'CONTEXT_NAME': 'tenant',  # Name in template context

        # Tenant-scoped presence backend
        'PRESENCE_BACKEND': 'tenant_redis',  # or 'tenant_memory'
        'PRESENCE_REDIS_URL': 'redis://localhost:6379/0',
    }

Template usage::

    {{ tenant.name }}
    {{ tenant.settings.theme }}
    {{ tenant.id }}
"""

from .resolvers import (
    TenantInfo,
    TenantResolver,
    SubdomainResolver,
    PathResolver,
    HeaderResolver,
    SessionResolver,
    CustomResolver,
    ChainedResolver,
    get_tenant_resolver,
    resolve_tenant,
    RESOLVER_REGISTRY,
)

from .mixin import (
    TenantMixin,
    TenantScopedMixin,
    TenantContextProcessor,
    context_processor,
)

from .middleware import (
    TenantMiddleware,
    get_current_tenant,
    set_current_tenant,
)

from .managers import (
    TenantManager,
    TenantQuerySet,
)

from .backends import (
    TenantAwareBackendMixin,
    TenantAwareRedisBackend,
    TenantAwareMemoryBackend,
    TenantPresenceManager,
    get_tenant_presence_backend,
)

__all__ = [
    # Tenant info
    "TenantInfo",
    # Resolvers
    "TenantResolver",
    "SubdomainResolver",
    "PathResolver",
    "HeaderResolver",
    "SessionResolver",
    "CustomResolver",
    "ChainedResolver",
    "get_tenant_resolver",
    "resolve_tenant",
    "RESOLVER_REGISTRY",
    # Mixins
    "TenantMixin",
    "TenantScopedMixin",
    "TenantContextProcessor",
    "context_processor",
    # Backends
    "TenantAwareBackendMixin",
    "TenantAwareRedisBackend",
    "TenantAwareMemoryBackend",
    "TenantPresenceManager",
    "get_tenant_presence_backend",
]
