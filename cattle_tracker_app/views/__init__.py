# cattle_tracker_app/views/__init__.py
# Make cattle_views a hard import (raise if broken), then soft-import the rest.
from .cattle_views import *  # exposes CattleDetailView and cattle_list
from importlib import import_module
import sys, traceback

# ---- hard import: cattle_views (so errors are visible) ----
try:
    _cv = import_module(f"{__name__}.cattle_views")
except Exception as e:
    print(f"[views.__init__] Failed to import {__name__}.cattle_views: {e}", file=sys.stderr)
    traceback.print_exc()
    raise
else:
    for k, v in _cv.__dict__.items():
        if not k.startswith("_"):
            globals()[k] = v

# ---- soft imports: ignore if a module is missing/broken ----
def _soft_export(modname: str) -> None:
    try:
        m = import_module(f"{__name__}.{modname}")
    except Exception:
        return
    for k, v in m.__dict__.items():
        if not k.startswith("_"):
            globals()[k] = v

for _m in (
    "dashboard",
    "turnout_views",
    "herd_sire_views",
    "leased_bull_views",
    "pasture_views",
    "paddock_views",
    "owner_views",
    "health_views",
    "breeding_views",
    "alert_views",
    "alerts_settings_view",
    "reports",
):
    _soft_export(_m)

# tidy up
del import_module, sys, traceback, _soft_export, _m, _cv
