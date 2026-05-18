# 🍽️ Inventory & Order Management App

A lightweight full-stack web application built with **Python, Flask, and SQLite** for managing restaurant kitchen inventory, menu items, and customer orders.

Built as my final project for **IT School — Python Programming** (Nov 2025).

---

## 📸 Preview

![App Screenshot](inventory_app.PNG)

---

## 🚀 Features

- **Ingredient Management** — Add, edit, and delete ingredients with quantity and unit tracking
- **Low Stock Alerts** — Automatic alerts when stock drops below 3x the required quantity per dish
- **Menu Management** — Create dishes with linked ingredients, quantities, and pricing
- **Order Management** — Place multi-item orders with automatic stock deduction
- **VAT Calculation** — 21% VAT included in all billing
- **Order Filtering** — Filter orders by dish name and date range
- **CSV Export** — Export full order history to CSV for reporting and analysis

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask, SQLite3 |
| Frontend | HTML, CSS |
| Database | SQLite (inventory.db) |
| Export | CSV via Python's io module |

---

## 📁 Project Structure

```
FinalProject/
├── app.py              # Main Flask application & routes
├── database.py         # Database logic & queries
├── inventory.db        # SQLite database
├── static/
│   └── style.css       # Styling
└── templates/
    ├── index.html          # Main dashboard
    ├── add_dish.html       # Add new dish
    ├── edit_dish.html      # Edit existing dish
    ├── edit_ingredient.html
    ├── new_order.html      # Place new order
    └── order_detail.html   # View order bill
```

---

## ⚙️ Installation & Setup

1. **Clone the repository**
```bash
git clone https://github.com/FloooT/Final_Project_IT_School.git
cd Final_Project_IT_School
```

2. **Create a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install flask
```

4. **Run the app**
```bash
python app.py
```

5. **Open in browser**
```
http://127.0.0.1:5000
```

---

## 💡 Why I Built This

I work in procurement and operations, managing purchase orders, vendor relationships, and inventory across multiple countries. I wanted to apply my Python learning to a real business problem I understand deeply — stock management, order tracking, and billing.

This project is the bridge between my operational background and my transition into Business Intelligence and data-driven tools.

---

## 📬 Contact

**Florian Trocan**
[LinkedIn](https://www.linkedin.com/in/floriantrocan/) · [GitHub](https://github.com/FloooT)
