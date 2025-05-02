# app/utils/auth.py
from flask import session, redirect, url_for, flash

def ensure_role(role):
    """
    Перевіряє, що:
      1) користувач увійшов (є session['user_id'])
      2) його роль = role
    Якщо ні — редіректить на login із flash-повідомленням.
    """
    if 'user_id' not in session:
        flash('Спочатку увійдіть', 'error')
        return redirect(url_for('auth.login'))
    if session.get('user_role') != role:
        flash('Немає доступу', 'error')
        return redirect(url_for('index'))
    # якщо все ок — нічого не повертаємо
