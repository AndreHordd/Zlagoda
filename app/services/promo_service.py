from datetime import date, timedelta
from app.utils.db import get_db, close_db

# за скільки днів до expiry_date включати акцію
PROMO_DAYS_BEFORE = 3

def apply_promotions():
    """
    Автоматично вмикає/вимикає акційність:
     - Вмикає акцію та робить знижку *0.8, якщо expiry_date <= today+3d
       і qty >= promo_threshold і зараз не в акції.
     - Вимикає прапорець, якщо товар більше не відповідає умовам.
    """
    conn = get_db()
    cur = conn.cursor()

    today       = date.today()
    cutoff_date = today + timedelta(days=PROMO_DAYS_BEFORE)

    # 1) Вмикаємо акцію та знижуємо ціну для тих, що відповідають
    cur.execute("""
        UPDATE Store_Product
           SET promotional_product = TRUE,
               selling_price       = ROUND(selling_price * 0.8, 4)
         WHERE expiry_date <= %s
           AND products_number >= promo_threshold
           AND promotional_product = FALSE
    """, (cutoff_date,))

    # 2) Вимикаємо акцію для тих, що більше не відповідають
    cur.execute("""
        UPDATE Store_Product
           SET promotional_product = FALSE
         WHERE (expiry_date > %s OR products_number < promo_threshold)
           AND promotional_product = TRUE
    """, (cutoff_date,))

    conn.commit()
    close_db(conn)
