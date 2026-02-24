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

from .audit import (
    AuditBackend,
    AuditEvent,
    CallbackAuditBackend,
    DatabaseAuditBackend,
    LoggingAuditBackend,
    audit_action,
    emit_audit,
    get_audit_backend,
)
from .backends import (
    TenantAwareBackendMixin,
    TenantAwareMemoryBackend,
    TenantAwareRedisBackend,
    TenantPresenceManager,
    get_tenant_presence_backend,
)
from .managers import (
    TenantManager,
    TenantQuerySet,
)
from .middleware import (
    TenantMiddleware,
    get_current_tenant,
    set_current_tenant,
)
from .mixin import (
    TenantContextProcessor,
    TenantMixin,
    TenantScopedMixin,
    context_processor,
)
from .resolvers import (
    RESOLVER_REGISTRY,
    ChainedResolver,
    CustomResolver,
    HeaderResolver,
    PathResolver,
    SessionResolver,
    SubdomainResolver,
    TenantInfo,
    TenantResolver,
    get_tenant_resolver,
    resolve_tenant,
)

# AuditLog model available via djust_tenants.models (not imported here
# to avoid AppRegistryNotReady during Django app loading)
from .security import (
    SecurityHeadersMiddleware,
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
    # Middleware
    "TenantMiddleware",
    "get_current_tenant",
    "set_current_tenant",
    # Managers
    "TenantManager",
    "TenantQuerySet",
    # Mixins
    "TenantMixin",
    "TenantScopedMixin",
    "TenantContextProcessor",
    "context_processor",
    # Audit
    "AuditEvent",
    "AuditBackend",
    "LoggingAuditBackend",
    "DatabaseAuditBackend",
    "CallbackAuditBackend",
    "get_audit_backend",
    "emit_audit",
    "audit_action",
    # Security
    "SecurityHeadersMiddleware",
    # Backends
    "TenantAwareBackendMixin",
    "TenantAwareRedisBackend",
    "TenantAwareMemoryBackend",
    "TenantPresenceManager",
    "get_tenant_presence_backend",
]
