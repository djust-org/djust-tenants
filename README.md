# djust-tenants (DEPRECATED)

**This package is deprecated.** All functionality has been folded into the main [djust](https://github.com/johnrtipton/djust) package as of djust v0.5.0. Install djust and import from `djust.tenants` instead.

Installing this package will emit a `DeprecationWarning` on import and pull in djust as a dependency, so existing code keeps working — but you should migrate.

## Migration

### Before (v0.x):
```
pip install djust-tenants
```
```python
from djust_tenants import TenantMixin, resolve_tenant
```

### After:
```
pip install djust
```
```python
from djust.tenants import TenantMixin, resolve_tenant
```

See [MIGRATION.md](MIGRATION.md) for the full import mapping.

## Why the consolidation?

djust v0.5.0 folded auth, tenants, admin, theming, and components into the core package. One install, one version number, one dependency pin. See the djust [MANIFESTO](https://djust.org/MANIFESTO_IDEAS.md) ("Complexity Is the Enemy") and the package consolidation plan for details.
