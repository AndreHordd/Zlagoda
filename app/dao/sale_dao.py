from app.utils.db import get_db, close_db

def delete_sale(upc: str, check_number: str) -> bool:
    """
    Видаляє один рядок продажу (комбінація UPC + check_number).
    Повертає True, якщо було видалено, і False — якщо такий рядок відсутній.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM Sale WHERE UPC=%s AND check_number=%s",
        (upc, check_number)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
