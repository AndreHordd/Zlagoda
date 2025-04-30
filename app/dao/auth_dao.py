from app.utils.db import get_db, close_db

def get_user_by_username(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password_hash, role, employee_id "
        "FROM auth_user WHERE username = %s",
        (username,)
    )
    user = cur.fetchone()
    close_db(conn)
    return user  # None або (id, pw_hash, role, employee_id)

def create_user(username, password_hash, role, employee_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO auth_user "
        "(username, password_hash, role, employee_id) "
        "VALUES (%s, %s, %s, %s)",
        (username, password_hash, role, employee_id)
    )
    conn.commit()
    close_db(conn)
