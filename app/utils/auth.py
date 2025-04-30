from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(role=None):
    """
    Декоратор, що перевіряє наявність session['user_id'].
    Якщо role задана — перевіряє session['user_role'].
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            if role and session.get('user_role') != role:
                flash('Немає доступу до цієї сторінки', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator
