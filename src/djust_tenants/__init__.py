"""
djust-tenants — now part of djust.

This package has been folded into djust core. Install djust instead:

    pip install djust

All functionality is now available at djust.tenants.
"""
import warnings

warnings.warn(
    "djust-tenants is deprecated. Use 'pip install djust' and import "
    "from djust.tenants instead. See MIGRATION.md for details.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the new djust location
from djust.tenants import *  # noqa: F401, F403, E402

try:
    from djust.tenants import __all__  # noqa: E402, F401
except ImportError:
    __all__ = []

__version__ = "99.0.0"
