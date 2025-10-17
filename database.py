import sqlite3
from datetime import datetime, date

DB_PATH = "inventory.db"
allowed_units = {"g", "pc", "ml"}
vatRate = 0.21  # 21%

# Database setup
def get_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Create tables
def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL UNIQUE,
                quantity_in_stock REAL DEFAULT 0,
                unit TEXT NOT NULL
            )
                     """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS menu_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish_name TEXT NOT NULL UNIQUE,
                dish_price REAL NOT NULL
            )
                     """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS dish_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity_needed REAL NOT NULL,
                FOREIGN KEY (ingredient_id) REFERENCES stock_inventory (id),
                FOREIGN KEY (menu_id) REFERENCES menu_inventory (id) ON DELETE CASCADE
            )
                     """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal REAL NOT NULL,
                vat_rate REAL NOT NULL,
                vat_amount REAL NOT NULL,
                total REAL NOT NULL
            )
                     """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                dish_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                line_price REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY(dish_id) REFERENCES menu_inventory(id)
            )
                     """)

    conn.close()

# Utilities - validate unit and ensure ingredient exists
def validate_unit(unit):
    unit = (unit or "").strip()
    return unit if unit in allowed_units else None

def ensure_ingredient_exists(conn, ingredient_name: str, unit: str):
    row = conn.execute("SELECT id, unit FROM stock_inventory WHERE ingredient_name = ?", (ingredient_name,)).fetchone()
    if row:
        if row["unit"] != unit:
            return None, f"Unit mismatch for {ingredient_name}: existing '{row['unit']}', given '{unit}'"
        return row["id"], None
    conn.execute("INSERT INTO stock_inventory (ingredient_name, quantity_in_stock, unit) VALUES (?, ?, ?)",
                 (ingredient_name, 0, unit))
    row = conn.execute("SELECT id FROM stock_inventory WHERE ingredient_name = ?", (ingredient_name,)).fetchone()
    return row["id"], None

# Add Ingredients
def add_ingredient(name: str, quantity: float, unit: str):
    if quantity <= 0:
        return False, "Quantity must be greater than 0"
    unit = validate_unit(unit)
    if not unit:
        return False, f"Unit must be one of {sorted(allowed_units)}"
    conn = get_connection()
    try:
        with conn:
            conn.execute("INSERT INTO stock_inventory (ingredient_name, quantity_in_stock, unit) VALUES (?, ?, ?)",
                         (name, quantity, unit))
        return True, "Ingredient added"
    except sqlite3.IntegrityError:
        return False, "Ingredient already exists"
    finally:
        conn.close()

# List Ingredients
def fetch_ingredients(filter_name=None, filter_quantity=None, op="ge"):
    conn = get_connection()
    sql = "SELECT * FROM stock_inventory WHERE 1=1"
    params = []
    if filter_name:
        sql += " AND ingredient_name LIKE ?"
        params.append(f"%{filter_name}%")
    if filter_quantity is not None:
        sql += " AND quantity_in_stock >= ?" if op == "ge" else " AND quantity_in_stock <= ?"
        params.append(filter_quantity)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Update Ingredients
def update_ingredient_by_id(ingredient_id: int, name: str, quantity: float, unit: str):
    if quantity <= 0:
        return False, "Quantity must be greater than 0"
    unit = validate_unit(unit)
    if not unit:
        return False, f"Unit must be one of {sorted(allowed_units)}"
    conn = get_connection()
    with conn:
        c = conn.execute("UPDATE stock_inventory SET ingredient_name = ?, quantity_in_stock = ?, unit = ? WHERE id = ?",
                         (name, quantity, unit, ingredient_id))
        ok = c.rowcount != 0
    conn.close()
    return (True, "Ingredient updated") if ok else (False, "Ingredient not found")

# Delete Ingredients
def delete_ingredient_by_id(ingredient_id: int):
    conn = get_connection()
    with conn:
        c = conn.execute("DELETE FROM stock_inventory WHERE id = ?", (ingredient_id,))
        ok = c.rowcount != 0
    conn.close()
    return (True, "Ingredient deleted") if ok else (False, f"Ingredient {ingredient_id} not found")

# Menu / Dishes
# Add Dish
def create_dish(dish_name: str, dish_price: float, ingredients: list):
    if dish_price <= 0:
        return False, "Price must be greater than 0"
    conn = get_connection()
    try:
        with conn:
            conn.execute("INSERT INTO menu_inventory (dish_name, dish_price) VALUES (?, ?)", (dish_name, dish_price))
            dish_id = conn.execute("SELECT id FROM menu_inventory WHERE dish_name = ?", (dish_name,)).fetchone()["id"]
            for ing in ingredients:
                unit = ing.get("unit")
                if not validate_unit(unit):
                    raise ValueError(f"Invalid unit for {ing.get('name')}")
                qty = float(ing.get("qty_needed"))
                if qty <= 0:
                    raise ValueError(f"Quantity needed must be greater than 0 for {ing.get('name')}")
                ing_id, err = ensure_ingredient_exists(conn, ing["name"], unit)
                if err:
                    raise ValueError(err)
                conn.execute("INSERT INTO dish_ingredients (menu_id, ingredient_id, quantity_needed) VALUES (?, ?, ?)",
                             (dish_id, ing_id, qty))
        return True, f"Dish '{dish_name}' created"
    except sqlite3.IntegrityError:
        return False, "Dish already exists"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# List Dishes
def fetch_menu(filter_name=None, filter_price=None, price_op="le"):
    conn = get_connection()
    sql = "SELECT * FROM menu_inventory WHERE 1=1"
    params = []
    if filter_name:
        sql += " AND dish_name LIKE ?"
        params.append(f"%{filter_name}%")
    if filter_price is not None:
        sql += " AND dish_price <= ?" if price_op == "le" else " AND dish_price >= ?"
        params.append(filter_price)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Fetch all ingredients required for a specific dish
def fetch_dish_ingredients(dish_id: int):
    conn = get_connection()
    rows = conn.execute(
        """SELECT di.quantity_needed, si.id as ing_id, si.ingredient_name, si.quantity_in_stock, si.unit
           FROM dish_ingredients di
           JOIN stock_inventory si ON si.id = di.ingredient_id
           WHERE di.menu_id = ?""", (dish_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Update Dish
def update_dish(dish_id: int, new_name: str, new_price: float, new_ingredients: list):
    if new_price <= 0:
        return False, "Price must be greater than 0"
    conn = get_connection()
    with conn:
        row = conn.execute("SELECT id FROM menu_inventory WHERE id = ?", (dish_id,)).fetchone()
        if not row:
            conn.close()
            return False, f"Dish {dish_id} not found"
        conn.execute("UPDATE menu_inventory SET dish_name = ?, dish_price = ? WHERE id = ?", (new_name, new_price, dish_id))
        conn.execute("DELETE FROM dish_ingredients WHERE menu_id = ?", (dish_id,))
        for ing in new_ingredients:
            unit = ing.get("unit")
            if not validate_unit(unit):
                conn.close()
                return False, f"Invalid unit for {ing.get('name')}"
            qty = float(ing.get("qty_needed"))
            if qty <= 0:
                conn.close()
                return False, f"Quantity needed must be greater than 0 for {ing.get('name')}"
            ing_id, err = ensure_ingredient_exists(conn, ing["name"], unit)
            if err:
                conn.close()
                return False, err
            conn.execute("INSERT INTO dish_ingredients (menu_id, ingredient_id, quantity_needed) VALUES (?, ?, ?)",
                         (dish_id, ing_id, qty))
    conn.close()
    return True, "Dish updated"

# Delete Dish
def delete_dish(dish_id: int):
    conn = get_connection()
    with conn:
        c = conn.execute("DELETE FROM menu_inventory WHERE id = ?", (dish_id,))
        ok = c.rowcount != 0
    conn.close()
    return (True, "Dish deleted") if ok else (False, "Dish not found")

# Orders and alerts
def compute_low_stock_alerts():
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.ingredient_name, si.quantity_in_stock, si.unit, di.quantity_needed
           FROM dish_ingredients di
           JOIN stock_inventory si ON si.id = di.ingredient_id"""
    ).fetchall()
    alerts = []
    seen = set()
    for r in rows:
        threshold = 3 * r["quantity_needed"]
        if r["quantity_in_stock"] < threshold:
            key = (r["ingredient_name"], r["unit"])
            if key in seen:
                continue
            seen.add(key)
            alerts.append({
                "ingredient": r["ingredient_name"],
                "stock": r["quantity_in_stock"],
                "unit": r["unit"],
                "threshold": threshold
            })
    conn.close()
    return alerts

# Create Order
def create_order(items: list):
    conn = get_connection()
    try:
        dish_map = {}
        subtotal = 0.0
        # validate items and compute subtotal
        for it in items:
            dish_id = int(it["dish_id"])
            qty = int(it["qty"])
            if qty <= 0:
                return False, "Quantity must be >= 1"
            row = conn.execute("SELECT id, dish_name, dish_price FROM menu_inventory WHERE id = ?", (dish_id,)).fetchone()
            if not row:
                return False, f"Dish id {dish_id} not found"
            dish_map[dish_id] = {"name": row["dish_name"], "price": float(row["dish_price"])}
            subtotal += float(row["dish_price"]) * qty

        vat_amount = round(subtotal * vatRate, 2)
        total = round(subtotal + vat_amount, 2)

        # accumulate ingredient needs
        needs = {}
        for it in items:
            dish_id = int(it["dish_id"])
            qty = int(it["qty"])
            ing_rows = conn.execute(
                "SELECT di.ingredient_id, di.quantity_needed, si.ingredient_name, si.quantity_in_stock, si.unit "
                "FROM dish_ingredients di JOIN stock_inventory si ON si.id = di.ingredient_id WHERE di.menu_id = ?",
                (dish_id,)
            ).fetchall()
            if not ing_rows:
                return False, f"Dish {dish_map[dish_id]['name']} has no ingredients defined"
            for r in ing_rows:
                tot_needed = float(r["quantity_needed"]) * qty
                iid = r["ingredient_id"]
                if iid in needs:
                    needs[iid]["needed"] += tot_needed
                else:
                    needs[iid] = {"name": r["ingredient_name"], "unit": r["unit"], "needed": tot_needed, "stock": r["quantity_in_stock"]}

        # check stock sufficiency
        for iid, info in needs.items():
            if info["stock"] < info["needed"]:
                return False, f"Not enough {info['name']} (need {info['needed']}{info['unit']}, have {info['stock']}{info['unit']})"

        # insert order and subtract stock atomically
        with conn:
            cur = conn.execute("INSERT INTO orders (subtotal, vat_rate, vat_amount, total) VALUES (?, ?, ?, ?)",
                               (round(subtotal, 2), vatRate, vat_amount, total))
            order_id = cur.lastrowid
            for it in items:
                dish_id = int(it["dish_id"])
                qty = int(it["qty"])
                line_price = round(dish_map[dish_id]["price"] * qty, 2)
                conn.execute("INSERT INTO order_items (order_id, dish_id, quantity, line_price) VALUES (?, ?, ?, ?)",
                             (order_id, dish_id, qty, line_price))
            for iid, info in needs.items():
                new_stock = info["stock"] - info["needed"]
                conn.execute("UPDATE stock_inventory SET quantity_in_stock = ? WHERE id = ?", (new_stock, iid))
        return True, order_id
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# List Orders
def fetch_orders(filter_name=None, start_date=None, end_date=None):
    conn = get_connection()
    sql = """SELECT o.id, o.order_date, o.subtotal, o.vat_rate, o.vat_amount, o.total
             FROM orders o
             WHERE 1=1"""
    params = []
    if start_date:
        sql += " AND date(o.order_date) >= date(?)"
        params.append(start_date)
    if end_date:
        sql += " AND date(o.order_date) <= date(?)"
        params.append(end_date)
    sql += " ORDER BY o.order_date DESC"
    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        order = dict(r)
        raw = order.get("order_date")
        display = ""
        try:
            if raw is None:
                display = ""
            elif isinstance(raw, str):
                # try iso parse first
                try:
                    dt = datetime.fromisoformat(raw)
                    display = dt.strftime("%Y-%m-%d")
                except Exception:
                    # try common formats
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                        try:
                            dt = datetime.strptime(raw, fmt)
                            display = dt.strftime("%Y-%m-%d")
                            break
                        except Exception:
                            continue
                    if display == "":
                        display = raw
            elif isinstance(raw, datetime):
                display = raw.strftime("%Y-%m-%d")
            elif isinstance(raw, date):
                display = raw.strftime("%Y-%m-%d")
            else:
                display = str(raw)
        except Exception:
            display = str(raw)
        order["order_date_display"] = display

        items_rows = conn.execute(
            """SELECT oi.quantity, oi.line_price, m.dish_name
               FROM order_items oi JOIN menu_inventory m ON m.id = oi.dish_id
               WHERE oi.order_id = ?""", (order["id"],)
        ).fetchall()
        items = [dict(it) for it in items_rows]
        if filter_name:
            if not any(filter_name.lower() in it["dish_name"].lower() for it in items):
                continue
        results.append({"order": order, "items": items})
    conn.close()
    return results
