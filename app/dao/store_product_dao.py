from app.utils.db import get_db, close_db

# ──────────────── CREATE ────────────────
def create_store_product(upc: str,
                         upc_prom: str | None,
                         product_id: int,
                         price: float,
                         qty: int,
                         promo: bool,
                         expiry_date: str,
                         promo_threshold: int):
    """
    Додає новий товар у магазин.
    expiry_date: строка 'YYYY-MM-DD'
    promo_threshold: одиниць для переходу в акцію
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO Store_Product
            (UPC, UPC_prom, id_product, selling_price,
             products_number, promotional_product,
             expiry_date, promo_threshold)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (upc, upc_prom, product_id, price,
         qty, promo, expiry_date, promo_threshold)
    )
    conn.commit()
    close_db(conn)

# ──────────────── READ BY UPC ────────────────
def get_store_product(upc: str) -> dict | None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT selling_price, products_number,
               promotional_product,
               expiry_date, promo_threshold
          FROM Store_Product
         WHERE UPC = %s
        """,
        (upc,)
    )
    row = cur.fetchone()
    close_db(conn)
    if row:
        return {
            'upc': upc,
            'price': float(row[0]),
            'quantity': row[1],
            'promotional': row[2],
            'expiry_date': row[3].isoformat(),
            'promo_threshold': row[4]
        }
    return None

# ──────────────── UPDATE ────────────────
def update_store_product(upc: str,
                         upc_prom: str | None,
                         product_id: int,
                         price: float,
                         qty: int,
                         promo: bool,
                         expiry_date: str,
                         promo_threshold: int) -> bool:
    """
    Оновлює всі поля товару у магазині
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Store_Product
           SET UPC_prom=%s,
               id_product=%s,
               selling_price=%s,
               products_number=%s,
               promotional_product=%s,
               expiry_date=%s,
               promo_threshold=%s
         WHERE UPC=%s
        """,
        (upc_prom, product_id, price,
         qty, promo,
         expiry_date, promo_threshold,
         upc)
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
