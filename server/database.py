import sqlite3
from datetime import datetime
import logging

# Path of the SQLite database file
DB_PATH = "carbon0.db"


def get_connection():
    """Create and return a SQLite connection object."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-style access to rows
    return conn


def init_db():
    """Create the database and tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Create the main products table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        name TEXT,
        category TEXT,
        brand TEXT,
        price REAL,
        web_url TEXT,
        image_url TEXT,
        cf_value REAL,
        cf_detail TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()
    logging.info("Database initialized at %s", DB_PATH)



def insert_product(product):
    """
    Insert or update a product in the database.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT OR REPLACE INTO products
        (sku, name, category, brand, price, web_url, image_url,
         cf_value, cf_detail, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        product.get("sku"),
        product.get("name"),
        product.get("category"),
        product.get("brand"),
        product.get("price"),
        product.get("web_url"),
        product.get("image_url"),
        product.get("cf_value"),
        product.get("cf_detail"),
        datetime.now(),
    ))

    conn.commit()
    conn.close()


def get_all_products():
    """Return all products as a list of dictionaries."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_product_by_sku(sku):
    """Retrieve a product by its SKU."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE sku = ?", (sku,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_product_by_sku(sku):
    """Delete a product from the database by its SKU."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE sku = ?", (sku,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
