# ⬇︎ ДОДАЙТЕ У КІНЕЦЬ ФАЙЛУ
import psycopg
from app.utils.db import get_db


def categories_sold_by_cashier():
    """
    Повертає для кожного касира:
      • id, прізвище, імʼя
      • кількість distinct категорій, що він продавав
      • загальну кількість проданих одиниць
    за весь час.
    """
    sql = """
        SELECT 
            e.id_employee,
            e.empl_surname,
            e.empl_name,
            COUNT(DISTINCT cat.category_name) AS num_categories_sold,
            SUM(s.product_number)           AS total_items_sold
        FROM Employee      e
        JOIN "check"       c  ON c.id_employee    = e.id_employee
        JOIN Sale          s  ON s.check_number   = c.check_number
        JOIN Store_Product sp ON sp.UPC           = s.UPC
        JOIN Product       p  ON p.id_product     = sp.id_product
        JOIN Category      cat ON cat.category_number = p.category_number
        WHERE e.empl_role = 'cashier'
        GROUP BY e.id_employee, e.empl_surname, e.empl_name
        ORDER BY num_categories_sold DESC, total_items_sold DESC
    """
    cur = get_db().cursor(row_factory=psycopg.rows.dict_row)
    cur.execute(sql)
    return cur.fetchall()


def category_price_stats(min_units: int):
    """② Min/Avg/Max ціни у категоріях, де stock > min_units."""
    sql = """
        SELECT c.category_name,
               MIN(sp.selling_price)           AS min_price,
               MAX(sp.selling_price)           AS max_price,
               ROUND(AVG(sp.selling_price),2)  AS avg_price,
               SUM(sp.products_number)         AS total_units
        FROM Category      c
        JOIN Product       p  ON p.category_number = c.category_number
        JOIN Store_Product sp ON sp.id_product     = p.id_product
        GROUP BY c.category_name
        HAVING SUM(sp.products_number) > %(m)s
        ORDER BY avg_price DESC
    """
    cur = get_db().cursor(row_factory=psycopg.rows.dict_row)
    cur.execute(sql, {"m": min_units})
    return cur.fetchall()


def cashiers_every_check_has_category(cat_name: str):
    """③ Касири, у кожному чеку яких є товар заданої категорії."""
    sql = """
        SELECT e.id_employee,
               e.empl_surname,
               e.empl_name
        FROM Employee e
        WHERE e.empl_role = 'cashier'
          AND NOT EXISTS (
                SELECT *      
                FROM "check" c
                WHERE c.id_employee = e.id_employee
                  AND NOT EXISTS (
                        SELECT *
                        FROM   Sale          s
                        JOIN   Store_Product sp ON sp.UPC        = s.UPC
                        JOIN   Product       p  ON p.id_product  = sp.id_product
                        JOIN   Category      cat ON cat.category_number = p.category_number
                        WHERE  s.check_number   = c.check_number
                          AND  cat.category_name = %(cat)s
                  )
          )
        ORDER BY e.empl_surname
    """
    cur = get_db().cursor(row_factory=psycopg.rows.dict_row)
    cur.execute(sql, {"cat": cat_name})
    return cur.fetchall()


def categories_without_promos(big_stock: int):
    """④ Категорії без акційних товарів і без stock > big_stock."""
    sql = """
        SELECT c.category_name
        FROM Category c
        WHERE NOT EXISTS (
              SELECT *
              FROM   Product p
              JOIN   Store_Product sp ON sp.id_product = p.id_product
              WHERE  p.category_number = c.category_number
                AND  sp.promotional_product = TRUE
        )
          AND NOT EXISTS (
              SELECT *
              FROM   Product p
              JOIN   Store_Product sp ON sp.id_product = p.id_product
              WHERE  p.category_number = c.category_number
                AND  sp.products_number > %(stock)s
        )
        ORDER BY c.category_name
    """
    cur = get_db().cursor(row_factory=psycopg.rows.dict_row)
    cur.execute(sql, {"stock": big_stock})
    return cur.fetchall()
