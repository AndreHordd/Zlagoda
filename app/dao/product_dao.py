from typing import List, Dict, Any
from app.utils.db import get_db, close_db

# ───────────────── CREATE ─────────────────
def create_product(category_number: int, name: str, characteristics: str) -> int:
    """
    Створює новий тип товару й повертає його id_product.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(id_product), 0) + 1 FROM Product")
    new_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO Product (
            id_product,
            category_number,
            product_name,
            characteristics
        ) VALUES (%s, %s, %s, %s)
        """,
        (new_id, category_number, name, characteristics)
    )
    conn.commit()
    close_db(conn)
    return new_id

# ───────────────── READ ─────────────────
def get_all_product_types(
    sort_by: str = 'name',
    order: str = 'asc',
    category: str | None = None,
    search: str | None = None
) -> list[dict]:
    """
    Повертає список типів товарів (таблиця Product),
    з полями id, назва, характеристики, виробник, категорія;
    підтримує фільтр за категорією та пошук по назві;
    сортування за довільною колонкою і напрямком.
    """
    cols = {
        'id':              'p.id_product',
        'name':            'p.product_name',
        'characteristics': 'p.characteristics',
        'manufacturer':    'p.manufacturer',
        'category':        'c.category_name'
    }
    sort_col  = cols.get(sort_by, cols['name'])
    sort_order= 'ASC' if order.lower()=='asc' else 'DESC'

    sql = [
        "SELECT",
        "  p.id_product,",
        "  p.product_name,",
        "  p.characteristics,",
        "  p.manufacturer,",
        "  c.category_name",
        "FROM Product AS p",
        "JOIN Category AS c",
        "  ON p.category_number = c.category_number"
    ]
    params = []
    where  = []

    if category:
        where.append("c.category_name = %s")
        params.append(category)
    if search:
        where.append("p.product_name ILIKE %s")
        params.append(f"%{search}%")

    if where:
        sql.append("WHERE " + " AND ".join(where))
    sql.append(f"ORDER BY {sort_col} {sort_order}")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("\n".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [
        {
            'id':              r[0],
            'name':            r[1],
            'characteristics': r[2],
            'manufacturer':    r[3],
            'category':        r[4]
        }
        for r in rows
    ]

def get_all_products(
    sort_by: str = 'name',
    order: str   = 'asc',
    category: str | None = None,
    promotional: bool | None = None,
    search: str | None = None,
    search_field: str = 'name'
) -> List[Dict[str, Any]]:
    """
    search_field ∈ {'name','upc','category','characteristics'}
    """
    cols = {
        'upc':  'sp.UPC',
        'name': 'p.product_name',
        'characteristics': 'p.characteristics',
        'category': 'c.category_name',
        'price': 'sp.selling_price',
        'quantity': 'sp.products_number',
        'promotional': 'sp.promotional_product'
    }
    sort_col   = cols.get(sort_by, cols['name'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    sql = [
        "SELECT sp.UPC,",
        "       p.product_name,",
        "       p.characteristics,",
        "       c.category_name,",
        "       sp.selling_price,",
        "       sp.products_number,",
        "       sp.promotional_product",
        "  FROM Store_Product AS sp",
        "  JOIN Product        AS p ON sp.id_product = p.id_product",
        "  JOIN Category       AS c ON p.category_number = c.category_number"
    ]
    params: list = []
    where:  list = []

    # ── фільтри
    if category:
        where.append("c.category_name = %s")
        params.append(category)
    if promotional is not None:
        where.append("sp.promotional_product = %s")
        params.append(promotional)

    # ── пошук
    if search:
        field_map = {
            'name':  "p.product_name ILIKE %s",
            'upc':   "sp.UPC = %s",
            'category': "c.category_name ILIKE %s",
            'characteristics': "p.characteristics ILIKE %s"
        }
        cond = field_map.get(search_field, field_map['name'])
        where.append(cond)
        params.append(f"%{search}%" if 'ILIKE' in cond else search)

    if where:
        sql.append(" WHERE " + " AND ".join(where))
    sql.append(f" ORDER BY {sort_col} {sort_order}")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("\n".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [
        {
            'upc':          r[0],
            'name':         r[1],
            'characteristics': r[2],
            'category':     r[3],
            'price':        float(r[4]),
            'quantity':     r[5],
            'promotional':  r[6]
        } for r in rows
    ]


# ───────────────── UPDATE ─────────────────
def update_product(prod_id: int, category_number: int, name: str, characteristics: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Product
           SET category_number=%s,
               product_name=%s,
               characteristics=%s
         WHERE id_product=%s
        """,
        (category_number, name, characteristics, prod_id)
    )
    conn.commit()
    updated = cur.rowcount > 0
    close_db(conn)
    return updated

# ───────────────── DELETE ─────────────────
def delete_product(prod_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Product WHERE id_product=%s", (prod_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
