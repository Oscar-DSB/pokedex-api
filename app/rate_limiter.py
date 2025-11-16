import os
import sys
from slowapi.util import get_remote_address

# ===========================================
# DETECCIÓN AUTOMÁTICA DE TESTING O PYTEST
# ===========================================

def is_testing_mode():
    """Detecta si estamos en pytest o en modo TESTING."""
    return (
        os.getenv("TESTING") == "true"
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )


# ===========================================
# RATE LIMITER GLOBAL
# ===========================================

if is_testing_mode():
    class DummyLimiter:
        """Limiter de prueba que no aplica límites."""
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def __getattr__(self, name):
            return lambda *a, **k: None

    limiter = DummyLimiter()
    print("RateLimiter DESACTIVADO (modo test detectado)")
else:
    from slowapi import Limiter
    limiter = Limiter(key_func=get_remote_address)
    print("RateLimiter ACTIVADO (modo normal)")
