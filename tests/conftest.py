"""Test bootstrap for the source-tree package layout.

The application intentionally exposes modules from ``app/`` as top-level
packages in both Docker and CI.  Some runners can have an unrelated third-
party package named ``telegram`` installed before collection.  Ensure the
source-tree package wins so tests exercise tgdrive's Telegram adapter.
"""

import importlib
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
app_dir = str(APP_DIR)
if app_dir in sys.path:
    sys.path.remove(app_dir)
sys.path.insert(0, app_dir)

module = sys.modules.get("telegram")
module_file = getattr(module, "__file__", "") if module else ""
if module and not module_file.startswith(app_dir):
    sys.modules.pop("telegram", None)

importlib.invalidate_caches()
