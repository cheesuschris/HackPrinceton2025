import sys
import os
import json

# Ensure the server directory and project root are on sys.path so imports work
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    # .../server/utils
SERVER_DIR = os.path.dirname(SCRIPT_DIR)                    # .../server
PROJECT_ROOT = os.path.dirname(SERVER_DIR)                  # .../Projects/HackPrinceton2025

# Prepend SERVER_DIR and PROJECT_ROOT so 'import database' or 'from server import database' succeed
for p in (SERVER_DIR, PROJECT_ROOT):
    if p and p not in sys.path:
        sys.path.insert(0, p)

# Try imports that work both when running from project root and from server/
# Prefer direct import of the module file `database.py` (import database)
# Fallback to package import (from server import database) if available
try:
    import database as db
except Exception:
    try:
        from server import database as db
    except Exception as e:
        print("Failed to import database module. sys.path:", sys.path[:5])
        raise

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            return []
        # Try full JSON array/object first
        try:
            data = json.loads(text)
            # If it's a single object, wrap to list
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            # Fallback to newline-delimited JSON (NDJSON)
            items = []
            f.seek(0)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
            return items
    return []

def normalize_product(p):
    out = {}
    out["sku"] = p.get("sku")
    out["name"] = p.get("name")
    out["category"] = p.get("category")
    out["brand"] = p.get("brand")
    price = p.get("price")
    out["price"] = float(price) if price not in (None, "") else None
    out["web_url"] = p.get("web_url")
    out["image_url"] = p.get("image_url")
    cf = p.get("cf_value")
    out["cf_value"] = float(cf) if cf not in (None, "") else None
    out["cf_detail"] = p.get("cf_detail")
    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: insert_product.py /path/to/products.json")
        sys.exit(2)

    json_path = sys.argv[1]
    if not os.path.isfile(json_path):
        print("File not found:", json_path)
        sys.exit(1)

    items = load_json(json_path)
    if not items:
        print("No items found in JSON.")
        sys.exit(0)

    # Ensure DB/tables exist
    db.init_db()

    inserted = 0
    failed = 0
    for i, raw in enumerate(items, start=1):
        try:
            prod = normalize_product(raw)
            if not prod.get("sku"):
                print(f"[WARN] item #{i} has no sku, skipping")
                failed += 1
                continue
            db.insert_product(prod)
            inserted += 1
        except Exception as e:
            print(f"[ERROR] failed to insert item #{i}: {e}")
            failed += 1

    print(f"Done. Inserted: {inserted}, Failed: {failed}, Total source items: {len(items)}")

if __name__ == "__main__":
    main()
