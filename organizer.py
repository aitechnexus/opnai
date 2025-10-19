"""Compatibility wrapper exposing the organizer CLI from the package."""
from mac_organizer import core as _core

for _name in dir(_core):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_core, _name)

del _name

__all__ = [name for name in globals() if not name.startswith("__")]
