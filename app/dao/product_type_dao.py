# app/dao/product_type_dao.py

from typing import List, Dict, Any
from app.utils.db import get_db, close_db

# ─────────────────── CREATE ───────────────────
def create_product_type(name: str, category_name: str) -> int:
    """
    Створює новий тип товару в таблиці Product.
    Знаходить category_number за category_name,
    створює запис і повертає новий id_product.
    """
    conn = get_db()
    cur = conn.cursor()
    # 1) Отримати номер категорії
    cur.execute(
        "SELECT category_number FROM Category WHERE category_name=%s",
        (category_name,)
    )
    row = cur.fetchone()
    if not row:
        close_db(conn)
        raise ValueError(f"Категорія «{category_name}» не знайдена")
    cat_num = row[0]

    # 2) Згенерувати новий id_product
    cur.execute("SELECT COALESCE(MAX(id_product),0)+1 FROM Product")
    new_id = cur.fetchone()[0]

    # 3) Вставити запис
    cur.execute(
        """
        INSERT INTO Product
            (id_product, category_number, product_name, characteristics)
        VALUES (%s, %s, %s, %s)
        """,
        (new_id, cat_num, name, "")
    )
    conn.commit()
    close_db(conn)
    return new_id


# ─────────────────── READ ───────────────────
def get_product_type_by_id(pt_id: int) -> Dict[str, Any] | None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id_product, p.product_name, c.category_name, p.characteristics
          FROM Product AS p
          JOIN Category AS c
            ON p.category_number = c.category_number
         WHERE p.id_product = %s
        """,
        (pt_id,)
    )
    row = cur.fetchone()
    close_db(conn)
    if not row:
        return None
    return {
        'id':              row[0],
        'name':            row[1],
        'category':        row[2],
        'characteristics': row[3]
    }


def get_all_product_types(
    sort_by: str = 'name',
    order: str   = 'asc',
    category: str|None = None,
    search:   str|None = None
) -> List[Dict[str, Any]]:
    # Використовуємо існуючий метод із product_dao
    from app.dao.product_dao import get_all_product_types as _g
    return _g(sort_by, order, category, search)


# ─────────────────── UPDATE ───────────────────
def update_product_type(pt_id: int, name: str, category_name: str) -> None:
    conn = get_db()
    cur = conn.cursor()
    # Отримати category_number
    cur.execute(
        "SELECT category_number FROM Category WHERE category_name=%s",
        (category_name,)
    )
    row = cur.fetchone()
    if not row:
        close_db(conn)
        raise ValueError(f"Категорія «{category_name}» не знайдена")
    cat_num = row[0]

    # Оновити запис
    cur.execute(
        """
        UPDATE Product
           SET product_name=%s,
               category_number=%s
         WHERE id_product=%s
        """,
        (name, cat_num, pt_id)
    )
    conn.commit()
    close_db(conn)


# ─────────────────── DELETE ───────────────────
def delete_product_type(pt_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Product WHERE id_product=%s", (pt_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
