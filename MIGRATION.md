# Migrating from `djust-tenants` to `djust.tenants`

This repo is deprecated. All functionality is now in the `djust` core package.

## 1. Replace the install

```diff
- pip install djust-tenants
+ pip install djust
```

## 2. Update imports

Grep-replace the top-level package name:

```bash
# macOS:
grep -rl 'djust_tenants' . | xargs sed -i '' 's/djust_tenants/djust.tenants/g'
# Linux:
grep -rl 'djust_tenants' . | xargs sed -i     's/djust_tenants/djust.tenants/g'
```

## 3. Import mapping

| Before                                 | After                           |
| -------------------------------------- | ------------------------------- |
| `from djust_tenants import X`          | `from djust.tenants import X`   |
| `import djust_tenants`                 | `from djust import tenants`     |
| `'djust_tenants'` in `INSTALLED_APPS`  | `'djust.tenants'`               |
| `DJUST_TENANTS` settings key           | `DJUST_TENANTS` (unchanged)     |

All public names (`TenantMixin`, `TenantResolver`, `SubdomainResolver`, `PathResolver`, `HeaderResolver`, `SessionResolver`, `CustomResolver`, `TenantMiddleware`, `get_current_tenant`, `set_current_tenant`, audit backends, etc.) are re-exported from `djust.tenants` with the same signatures.

## 4. Remove the old dep

Once imports are migrated and tests pass, remove `djust-tenants` from your `pyproject.toml` / `requirements.txt`. The shim package depends on `djust>=0.5.6rc1` so djust is already installed.
