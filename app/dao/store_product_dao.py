import random
from app.utils.db import get_db, close_db

def generate_upc() -> str:
    conn = get_db()
    cur = conn.cursor()
    while True:
        candidate = ''.join(random.choices('0123456789', k=12))
        cur.execute("SELECT 1 FROM Store_Product WHERE UPC=%s", (candidate,))
        if cur.fetchone() is None:
            close_db(conn)
            return candidate

def create_store_product(
    product_id: int,
    price: float,
    qty: int,
    expiry_date: str
) -> tuple[bool, str]:
    """
    Генерує UPC, вставляє новий рядок із UPC_prom=NULL.
    Повертає (успіх, upc).
    """
    upc = generate_upc()

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO Store_Product
               (UPC, UPC_prom, id_product,
                selling_price, products_number,
                promotional_product, expiry_date,
                promo_threshold)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (upc,     # головний код
             None,    # UPC_prom = NULL
             product_id,
             price,
             qty,
             False,       # неакційний
             expiry_date,
             0)           # поріг
        )
        conn.commit()
        return True, upc
    except Exception:
        conn.rollback()
        return False, ''
    finally:
        close_db(conn)


def update_store_product(
    upc: str,
    product_id: int,
    price: float,
    qty: int,
    expiry_date: str
) -> bool:
    """
    Оновлює поля, не змінюючи UPC та UPC_prom, без вибору акційності.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Store_Product
           SET id_product=%s,
               selling_price=%s,
               products_number=%s,
               expiry_date=%s
         WHERE UPC=%s
        """,
        (product_id, price, qty, expiry_date, upc)
    )
    conn.commit()
    ok = cur.rowcount > 0
    close_db(conn)
    return ok


def get_store_product_by_upc(upc: str) -> dict | None:
    """
    Читає товар і повертає словник:
    {'upc','upc_prom','product_id','price','quantity',
     'promotional','expiry_date','promo_threshold'}
    expiry_date як рядок 'YYYY-MM-DD' (SQL::TEXT).
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          UPC_prom,
          id_product,
          selling_price,
          products_number,
          promotional_product,
          expiry_date::TEXT,
          promo_threshold
        FROM Store_Product
        WHERE UPC = %s
        """,
        (upc,)
    )
    row = cur.fetchone()
    close_db(conn)
    if not row:
        return None
    return {
        'upc':            upc,
        'upc_prom':       row[0] or '',
        'product_id':     row[1],
        'price':          float(row[2]),
        'quantity':       row[3],
        'promotional':    row[4],
        'expiry_date':    row[5] or '',
        'promo_threshold':row[6]
    }

def delete_store_product(upc: str) -> bool:
    """
    Видаляє товар і лишає історію продажів (UPC_prom nullable).
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Store_Product WHERE UPC = %s", (upc,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted

def get_all_store_products() -> list[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT UPC, UPC_prom, id_product, selling_price, products_number, promotional_product, expiry_date::TEXT, promo_threshold FROM Store_Product")
    rows = cur.fetchall()
    close_db(conn)
    return [
        {
            'upc':             r[0],
            'upc_prom':        r[1] or '',
            'product_id':      r[2],
            'price':           float(r[3]),
            'quantity':        r[4],
            'promotional':     r[5],
            'expiry_date':     r[6] or '',
            'promo_threshold': r[7]
        }
        for r in rows
    ]

