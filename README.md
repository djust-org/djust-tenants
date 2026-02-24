# djust-tenants

Multi-tenancy package for Django and [djust](https://github.com/djust-org/djust) applications. Build SaaS apps with tenant isolation via subdomains, paths, headers, or custom resolution strategies.

## Features

- 🏢 **Flexible Tenant Resolution** - Subdomain, path, header, session, or custom resolvers
- 🔒 **Data Isolation** - Schema-based (PostgreSQL) or FK-based (any database)
- ⚡ **LiveView Integration** - Optional `TenantMixin` for djust LiveViews
- 🗄️ **Tenant-Scoped Backends** - Redis, memory, or database backends with tenant namespacing
- 🎯 **Zero Config** - Works with existing Django models or bring your own tenant model
- 🧪 **Well Tested** - Comprehensive test suite with real-world examples

## Installation

```bash
# Core (works with any Django project)
pip install djust-tenants

# With djust LiveView integration
pip install djust-tenants[djust]

# With Redis backend
pip install djust-tenants[redis]

# With PostgreSQL schema isolation
pip install djust-tenants[postgres]

# Everything
pip install djust-tenants[djust,redis,postgres]
```

## Quick Start

### 1. Add to Django Settings

```python
# settings.py

INSTALLED_APPS = [
    # ...
    "djust_tenants",
]

MIDDLEWARE = [
    # ...
    "djust_tenants.middleware.TenantMiddleware",  # Add after SessionMiddleware
]

# Tenant resolution strategy
DJUST_TENANTS = {
    "RESOLVER": "subdomain",  # subdomain, path, header, session, or custom
    "MAIN_DOMAIN": "myapp.com",
    "SUBDOMAIN_EXCLUDE": ["www", "api", "admin"],
}
```

### 2. Create Tenant Model (Optional)

```python
# myapp/models.py

from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)  # Used for subdomain
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
```

### 3. Use in Views

#### Standard Django View

```python
from django.views import View

class DashboardView(View):
    def get(self, request):
        # request.tenant is automatically set by middleware
        tenant = request.tenant

        # Query data scoped to current tenant
        projects = Project.objects.filter(tenant_id=tenant.id)

        return render(request, 'dashboard.html', {
            'tenant': tenant,
            'projects': projects,
        })
```

#### djust LiveView

```python
from djust import LiveView
from djust_tenants.mixins import TenantMixin

class DashboardView(TenantMixin, LiveView):
    template_name = 'dashboard.html'

    def mount(self, request, **kwargs):
        # self.tenant is automatically set by TenantMixin
        self.projects = Project.objects.filter(tenant=self.tenant.obj)

    def get_context_data(self, **kwargs):
        return {
            'tenant': self.tenant,
            'projects': self.projects,
        }
```

## Tenant Resolution Strategies

### Subdomain Routing

```
acme.myapp.com  → Organization(slug='acme')
startup.myapp.com → Organization(slug='startup')
```

```python
# settings.py
DJUST_TENANTS = {
    "RESOLVER": "subdomain",
    "MAIN_DOMAIN": "myapp.com",
    "SUBDOMAIN_EXCLUDE": ["www", "api", "admin"],
}
```

### Path-Based Routing

```
myapp.com/acme/dashboard  → Organization(slug='acme')
myapp.com/startup/reports → Organization(slug='startup')
```

```python
# settings.py
DJUST_TENANTS = {
    "RESOLVER": "path",
    "PATH_POSITION": 1,  # /org_slug/...
    "PATH_EXCLUDE": ["admin", "api", "static"],
}
```

### Header-Based Routing

```
X-Tenant-ID: acme → Organization(slug='acme')
```

```python
# settings.py
DJUST_TENANTS = {
    "RESOLVER": "header",
    "HEADER_NAME": "X-Tenant-ID",
}
```

### Session-Based Routing

```python
# settings.py
DJUST_TENANTS = {
    "RESOLVER": "session",
    "SESSION_KEY": "tenant_id",
}

# In view:
request.session['tenant_id'] = organization.id
```

### Custom Resolver

```python
# myapp/tenants.py
from djust_tenants.resolvers import TenantResolver, TenantInfo

class CustomResolver(TenantResolver):
    def resolve(self, request):
        # Your custom logic here
        tenant_id = request.GET.get('tenant')
        if tenant_id:
            org = Organization.objects.get(id=tenant_id)
            return TenantInfo(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                obj=org,
            )
        return None

# settings.py
DJUST_TENANTS = {
    "RESOLVER": "custom",
    "CUSTOM_RESOLVER": "myapp.tenants.CustomResolver",
}
```

## Data Isolation Strategies

### FK-Based (Works with Any Database)

```python
from django.db import models

class Project(models.Model):
    tenant = models.ForeignKey('myapp.Organization', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

# All queries must filter by tenant
projects = Project.objects.filter(tenant=request.tenant.obj)
```

**Pros**: Simple, works everywhere, easy migrations
**Cons**: Shared tables, risk of cross-tenant leaks

### Schema-Based (PostgreSQL Only)

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'djust_tenants.backends.postgres',
        'NAME': 'myapp',
        'TENANT_SCHEMA_PREFIX': 'tenant_',
    }
}

# Each tenant gets a separate schema:
# public schema (shared: users, organizations)
# tenant_acme schema (acme's data)
# tenant_startup schema (startup's data)

# Queries automatically scoped to current schema
projects = Project.objects.all()  # SELECT * FROM tenant_acme.projects
```

**Pros**: Strong isolation, great for compliance/security
**Cons**: PostgreSQL only, complex migrations

## Tenant-Scoped Backends

### Redis Backend (Namespaced Keys)

```python
# settings.py
DJUST_TENANTS = {
    "REDIS_URL": "redis://localhost:6379/0",
}

# In your code
from djust_tenants.backends import get_tenant_redis

def my_view(request):
    redis = get_tenant_redis(request.tenant)

    # Keys are automatically namespaced: tenant:{tenant_id}:mykey
    redis.set('mykey', 'myvalue')
    value = redis.get('mykey')
```

### Memory Backend (Isolated Storage)

```python
from djust_tenants.backends import get_tenant_memory

def my_view(request):
    storage = get_tenant_memory(request.tenant)

    storage['mykey'] = 'myvalue'
    value = storage.get('mykey')
```

## Template Usage

```django
{# dashboard.html #}
<h1>{{ tenant.name }} Dashboard</h1>
<p>Tenant ID: {{ tenant.id }}</p>
<p>Slug: {{ tenant.slug }}</p>

{% for project in projects %}
  <div>{{ project.name }}</div>
{% endfor %}
```

## Testing

```python
from django.test import TestCase
from djust_tenants.test import TenantTestCase

class MyTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        # self.tenant is automatically created

    def test_tenant_isolation(self):
        # Create data in current tenant
        project = Project.objects.create(
            tenant=self.tenant.obj,
            name='Test Project'
        )

        # Switch to different tenant
        other_tenant = self.create_tenant(slug='other')
        self.set_tenant(other_tenant)

        # Should not see previous tenant's data
        self.assertEqual(Project.objects.count(), 0)
```

## Examples

See the `examples/` directory for complete working examples:

- **examples/simple_saas/** - Minimal SaaS app with subdomain routing
- **examples/path_based/** - Path-based multi-tenancy
- **examples/djust_integration/** - Full djust LiveView integration
- **examples/schema_isolation/** - PostgreSQL schema-based isolation

## Advanced Usage

### Tenant Manager (Auto-Filter Querysets)

```python
from djust_tenants.managers import TenantManager

class Project(models.Model):
    tenant = models.ForeignKey('Organization', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    objects = TenantManager()  # Auto-filters by current tenant

# In view with request.tenant set:
projects = Project.objects.all()  # Automatically filtered by tenant
```

### Management Commands

```bash
# Run command for specific tenant
python manage.py my_command --tenant=acme

# Run command for all tenants
python manage.py my_command --all-tenants
```

### Audit Logging

```python
from djust_tenants.middleware import get_current_tenant

def my_view(request):
    tenant = get_current_tenant()

    # Log with tenant context
    logger.info("User action", extra={
        'tenant_id': tenant.id,
        'tenant_name': tenant.name,
    })
```

## Configuration Reference

```python
DJUST_TENANTS = {
    # Resolver type
    "RESOLVER": "subdomain",  # subdomain, path, header, session, custom

    # Subdomain options
    "MAIN_DOMAIN": "myapp.com",
    "SUBDOMAIN_EXCLUDE": ["www", "api", "admin"],

    # Path options
    "PATH_POSITION": 1,  # URL segment position (0-indexed)
    "PATH_EXCLUDE": ["admin", "api", "static"],

    # Header options
    "HEADER_NAME": "X-Tenant-ID",

    # Session options
    "SESSION_KEY": "tenant_id",

    # Custom resolver
    "CUSTOM_RESOLVER": "myapp.tenants.CustomResolver",

    # Behavior
    "REQUIRED": True,  # Raise 404 if no tenant found
    "DEFAULT": None,  # Default tenant if none resolved
    "CONTEXT_NAME": "tenant",  # Template context variable name

    # Backends
    "REDIS_URL": "redis://localhost:6379/0",
}
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **Documentation**: https://docs.djust.org/tenants
- **GitHub**: https://github.com/djust-org/djust-tenants
- **Issues**: https://github.com/djust-org/djust-tenants/issues
- **djust Framework**: https://github.com/djust-org/djust
