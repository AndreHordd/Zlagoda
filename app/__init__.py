"""
Головний factory файл Flask-застосунку.
"""

import datetime
import logging
import os
import sys
import traceback

from flask import (
    Flask, session, g, render_template,
    url_for, redirect, current_app, send_from_directory
)

from .utils.db import get_db, close_db

# ─── blueprints ─────────────────────────────────────────────────────────
from .api.auth            import auth_bp
from .views.manager.routes import manager_bp
from .views.cashier.routes import cashier_bp


# ────────────────────────────────────────────────────────────────────────
# factory-функція
# ────────────────────────────────────────────────────────────────────────
def create_app() -> Flask:
    # ─── базове створення ──────────────────────────────────────────────
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static',
        template_folder='templates'
    )
    app.config.from_object('app.config.Config')

    # ─── налагодження / логування ──────────────────────────────────────
    app.config.update(
        DEBUG=True,                  # режим відлагодження
        PROPAGATE_EXCEPTIONS=True    # пропускати винятки до Werkzeug
    )
    app.debug = True

    stream_h = logging.StreamHandler(sys.stderr)
    stream_h.setLevel(logging.ERROR)
    stream_h.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    )
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(stream_h)
    app.logger.setLevel(logging.ERROR)

    @app.errorhandler(Exception)
    def _log_unhandled(exc):
        """Логуємо повний traceback і повертаємо 500."""
        traceback.print_exc()
        return "Internal Server Error", 500

    # ─── реєстрація Blueprints (БЕЗ додаткових url_prefix!) ────────────
    # Кожен Blueprint уже містить свій власний prefix:
    #   * auth_bp       → '/auth'
    #   * manager_bp    → '/manager'
    #   * cashier_bp    → '/cashier'
    # Тому додавати prefix під час реєстрації не треба — інакше виходить
    # подвійний шлях типу  /auth/auth/login  або  /manager/manager/…
    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(cashier_bp)

    # ─── поточний користувач у g ───────────────────────────────────────
    @app.before_request
    def load_current_user():
        g.current_user = None
        if 'user_id' in session:
            conn = get_db()
            cur  = conn.cursor()
            cur.execute(
                """
                SELECT id, username, role, employee_id
                  FROM auth_user
                 WHERE id = %s
                """,
                (session['user_id'],)
            )
            row = cur.fetchone()
            if row:
                full_name = row[1]  # за замовчуванням — username
                if row[3]:          # є привʼязка до працівника
                    cur.execute(
                        """
                        SELECT empl_surname, empl_name
                          FROM Employee
                         WHERE id_employee = %s
                        """,
                        (row[3],)
                    )
                    emp = cur.fetchone()
                    if emp:
                        full_name = f"{emp[0]} {emp[1]}"

                # робимо легку proxy-«модель» User
                g.current_user = type(
                    'User', (), {
                        'id':       row[0],
                        'username': row[1],
                        'name':     full_name,
                        'role':     row[2]
                    }
                )
            close_db(conn)

    # ─── глобальні змінні для всіх шаблонів ────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            'current_user': getattr(g, 'current_user', None),
            'current_year': datetime.datetime.now().year
        }

    # ─── головна сторінка ──────────────────────────────────────────────
    @app.route('/')
    def index():
        # якщо вже залогінені — одразу на свій дашборд
        if getattr(g, 'current_user', None):
            return redirect(url_for(f"{g.current_user.role}.dashboard"))
        return render_template('index.html')

    # ─── favicon.ico (щоб уникнути 404 у логах) ────────────────────────
    @app.route('/favicon.ico')
    def favicon():
        path = os.path.join(current_app.root_path, 'static', 'img', 'favicon.ico')
        if os.path.exists(path):
            return send_from_directory(
                os.path.join(current_app.root_path, 'static', 'img'),
                'favicon.ico',
                mimetype='image/vnd.microsoft.icon'
            )
        return '', 204

    # ─── завершення ────────────────────────────────────────────────────
    return app
