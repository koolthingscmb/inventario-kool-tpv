"""Debug para ver la estructura de layout."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from kool_tpv.utils.widgets.payment_controllers import load_config

layout = load_config("layout_config.json")

# Navegar a payment_controllers
pc_layout = layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("payment_controllers", {})

print("=" * 70)
print("ESTRUCTURA DE payment_controllers en layout_config.json:")
print("=" * 70)
print(json.dumps(pc_layout, indent=2))
