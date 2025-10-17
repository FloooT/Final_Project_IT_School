from flask import Flask, request, render_template, redirect, url_for, flash, Response
import io, csv
from database import (
    init_db, fetch_ingredients, add_ingredient, update_ingredient_by_id,
    delete_ingredient_by_id, fetch_menu, create_dish, fetch_dish_ingredients,
    update_dish, delete_dish, compute_low_stock_alerts, fetch_orders,
    create_order, vatRate
)

app = Flask(__name__)
app.secret_key = "secretkey"

with app.app_context():
    init_db()

# Home
@app.route("/")
def index():
    ing_name = request.args.get("ing_name")
    ing_qty = request.args.get("ing_qty")
    ing_op = request.args.get("ing_op", "ge")
    try:
        ing_qty_val = float(ing_qty) if ing_qty else None
    except ValueError:
        ing_qty_val = None

    dish_name = request.args.get("dish_name")
    dish_price = request.args.get("dish_price")
    dish_op = request.args.get("dish_op", "le")
    try:
        dish_price_val = float(dish_price) if dish_price else None
    except ValueError:
        dish_price_val = None

    order_dish_name = request.args.get("order_dish_name")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    ingredients = fetch_ingredients(filter_name=ing_name, filter_quantity=ing_qty_val, op=ing_op)
    dishes = fetch_menu(filter_name=dish_name, filter_price=dish_price_val, price_op=dish_op)
    orders = fetch_orders(filter_name=order_dish_name, start_date=start_date, end_date=end_date)
    alerts = compute_low_stock_alerts()

    return render_template("index.html",
                           dishes=dishes, ingredients=ingredients, orders=orders,
                           ing_filters={"name": ing_name or "", "qty": ing_qty or "", "op": ing_op},
                           dish_filters={"name": dish_name or "", "price": dish_price or "", "op": dish_op},
                           order_filters={"name": order_dish_name or "", "start": start_date or "", "end": end_date or ""},
                           alerts=alerts, vat_rate=vatRate)

# New order Route
@app.route("/order/new", methods=["GET", "POST"])
def new_order():
    dishes = fetch_menu()
    prefill = request.args.get("prefill")  # optional: pass dish id to preselect
    if request.method == "POST":
        dish_ids = request.form.getlist("dish_id[]")
        qtys = request.form.getlist("qty[]")
        items = []
        for did, q in zip(dish_ids, qtys):
            if not did:
                continue
            try:
                qty = int(q)
            except Exception:
                qty = 0
            if qty <= 0:
                continue
            items.append({"dish_id": did, "qty": qty})
        if not items:
            flash("Select at least one dish with quantity greater than 0")
            return redirect(url_for("new_order"))
        ok, result = create_order(items)
        if not ok:
            flash(result)
            return redirect(url_for("new_order"))
        order_id = result
        flash("Order created")
        return redirect(url_for("order_detail", order_id=order_id))
    return render_template("new_order.html", dishes=dishes, vat_rate=vatRate, prefill=prefill)

# Orders details Route
@app.route("/order/<int:order_id>")
def order_detail(order_id):
    orders = fetch_orders()
    for o in orders:
        if o["order"]["id"] == order_id:
            return render_template("order_detail.html", order=o["order"], items=o["items"])
    flash("Order not found")
    return redirect(url_for("index"))

# Export CSV
@app.route("/export/orders.csv")
def export_orders_csv():
    orders = fetch_orders()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["order_id", "order_date", "dish_name", "qty", "line_price", "subtotal", "vat_rate", "vat_amount", "total"])
    for o in orders:
        order = o["order"]
        for it in o["items"]:
            writer.writerow([order["id"], order.get("order_date_display", ""), it["dish_name"], it["quantity"], it["line_price"],
                             order["subtotal"], order["vat_rate"], order["vat_amount"], order["total"]])
    output = si.getvalue()
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=orders.csv"})

# Ingredients CRUD
# Add Ingredient Route
@app.route("/add_ingredient", methods=["POST"])
def add_ingredient_route():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Ingredient name is required")
        return redirect(url_for("index"))
    try:
        quantity = float(request.form.get("quantity", 0))
    except ValueError:
        flash("Invalid quantity")
        return redirect(url_for("index"))
    if quantity <= 0:
        flash("Quantity must be greater than 0")
        return redirect(url_for("index"))
    unit = request.form.get("unit", "pc")
    ok, msg = add_ingredient(name, quantity, unit)
    flash(msg)
    return redirect(url_for("index"))

# Edit Ingredient Route
@app.route("/edit_ingredient/<int:ingredient_id>", methods=["GET", "POST"])
def edit_ingredient_route(ingredient_id):
    if request.method == "POST":
        new_name = request.form.get("new_name", "").strip()
        try:
            new_quantity = float(request.form.get("quantity", 0))
        except ValueError:
            flash("Invalid quantity")
            return redirect(url_for("index"))
        if new_quantity <= 0:
            flash("Quantity must be greater than 0")
            return redirect(url_for("index"))
        new_unit = request.form.get("unit", "pc")
        ok, msg = update_ingredient_by_id(ingredient_id, new_name, new_quantity, new_unit)
        flash(msg)
        return redirect(url_for("index"))
    ing_list = fetch_ingredients()
    ing = next((i for i in ing_list if i["id"] == ingredient_id), None)
    if not ing:
        flash("Ingredient not found")
        return redirect(url_for("index"))
    return render_template("edit_ingredient.html", ingredient=ing, units=sorted(("g","ml","pc")))

# Delete Ingredient Route
@app.route("/delete_ingredient/<int:ingredient_id>", methods=["POST"])
def delete_ingredient_route(ingredient_id):
    ok, msg = delete_ingredient_by_id(ingredient_id)
    flash(msg)
    return redirect(url_for("index"))

# Dishes CRUD
# Add Dish Route
@app.route("/add_dish", methods=["GET", "POST"])
def add_dish_route():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Dish name is required")
            return redirect(url_for("add_dish_route"))
        try:
            price = float(request.form.get("price", 0))
        except ValueError:
            flash("Invalid price")
            return redirect(url_for("add_dish_route"))
        if price <= 0:
            flash("Price must be greater than 0")
            return redirect(url_for("add_dish_route"))
        ing_names = request.form.getlist("item_name[]")
        ing_qtys = request.form.getlist("item_qty[]")
        ing_units = request.form.getlist("item_unit[]")
        ingredients = []
        for n, q, u in zip(ing_names, ing_qtys, ing_units):
            n = n.strip()
            if not n:
                continue
            try:
                qty = float(q)
            except Exception:
                flash(f"Invalid qty for ingredient '{n}'")
                return redirect(url_for("add_dish_route"))
            if qty <= 0:
                flash(f"Ingredient '{n}' quantity must be greater than 0")
                return redirect(url_for("add_dish_route"))
            ingredients.append({"name": n, "qty_needed": qty, "unit": u.strip() or "pc"})
        ok, msg = create_dish(name, price, ingredients)
        flash(msg)
        return redirect(url_for("index"))
    return render_template("add_dish.html", units=sorted(("g","ml","pc")))

# Edit Dish Route
@app.route("/edit_dish/<int:dish_id>", methods=["GET", "POST"])
def edit_dish_route(dish_id):
    dishes = fetch_menu()
    dish = next((d for d in dishes if d["id"] == dish_id), None)
    if not dish:
        flash("Dish not found")
        return redirect(url_for("index"))
    if request.method == "POST":
        new_name = request.form.get("new_name", "").strip()
        if not new_name:
            flash("Dish name is required")
            return redirect(url_for("edit_dish_route", dish_id=dish_id))
        try:
            new_price = float(request.form.get("price", 0))
        except ValueError:
            flash("Invalid price")
            return redirect(url_for("edit_dish_route", dish_id=dish_id))
        if new_price <= 0:
            flash("Price must be greater than 0")
            return redirect(url_for("edit_dish_route", dish_id=dish_id))
        ing_names = request.form.getlist("item_name[]")
        ing_qtys = request.form.getlist("item_qty[]")
        ing_units = request.form.getlist("item_unit[]")
        ingredients = []
        for n, q, u in zip(ing_names, ing_qtys, ing_units):
            n = n.strip()
            if not n:
                continue
            try:
                qty = float(q)
            except Exception:
                flash(f"Invalid qty for ingredient '{n}'")
                return redirect(url_for("edit_dish_route", dish_id=dish_id))
            if qty <= 0:
                flash(f"Ingredient '{n}' quantity must be greater than 0")
                return redirect(url_for("edit_dish_route", dish_id=dish_id))
            ingredients.append({"name": n, "qty_needed": qty, "unit": u.strip() or "pc"})
        ok, msg = update_dish(dish_id, new_name, new_price, ingredients)
        flash(msg)
        return redirect(url_for("index"))
    current_ings = fetch_dish_ingredients(dish_id)
    return render_template("edit_dish.html", dish=dish, current_ings=current_ings, units=sorted(("g","ml","pc")))

# Delete Dish Route
@app.route("/delete_dish/<int:dish_id>", methods=["POST"])
def delete_dish_route(dish_id):
    ok, msg = delete_dish(dish_id)
    flash(msg)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
