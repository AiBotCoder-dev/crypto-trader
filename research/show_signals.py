import json
import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "data.json")
d = json.load(open(path, encoding="utf-8"))
for s in d["signals"]:
    print(
        f"{s['pair']:<10} price {s['price']:>12} regime {s['regime']:<8} "
        f"entry@ {s['entry_level']:>12} dist {s['distance_pct']:>7}%"
    )
