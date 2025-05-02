from app.utils.db import get_db, close_db

# ──────────────── CREATE ────────────────
def create_store_product(upc: str, upc_prom: str | None, product_id: int,
                         price: float, qty: int, promo: bool):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO Store_Product
               (UPC, UPC_prom, id_product, selling_price,
                products_number, promotional_product)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (upc, upc_prom, product_id, price, qty, promo)
    )
    conn.commit()
    close_db(conn)

# ──────────────── READ BY UPC ────────────────
def get_store_product(upc: str) -> dict | None:
    """
    Повертає словник {'upc', 'price', 'quantity'} або None, якщо не знайдено.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT selling_price, products_number "
        "FROM Store_Product WHERE UPC = %s",
        (upc,)
    )
    row = cur.fetchone()
    close_db(conn)
    if row:
        return {
            'upc': upc,
            'price': float(row[0]),
            'quantity': row[1]
        }
    return None

# ──────────────── UPDATE ────────────────
def update_store_product(upc: str, upc_prom: str | None, product_id: int,
                         price: float, qty: int, promo: bool) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Store_Product
           SET UPC_prom=%s,
               id_product=%s,
               selling_price=%s,
               products_number=%s,
               promotional_product=%s
         WHERE UPC=%s
        """,
        (upc_prom, product_id, price, qty, promo, upc)
    )
    conn.commit()
    updated = cur.rowcount > 0
    close_db(conn)
    return updated

# ──────────────── DELETE ────────────────
def delete_store_product(upc: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Store_Product WHERE UPC=%s", (upc,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
