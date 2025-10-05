# app/__init__.py

import datetime
import logging
import os
import sys
import traceback

from flask import (
    Flask, session, g, render_template,
    url_for, redirect, current_app,
    send_from_directory
)

from .utils.db import get_db, close_db, db_available
from .api.auth import auth_bp
from .views.manager.routes import manager_bp
from .views.cashier.routes import cashier_bp


def create_app() -> Flask:
    # ------------------------------------------------------------------
    # базове створення застосунку
    # ------------------------------------------------------------------
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static',
        template_folder='templates'
    )
    app.config.from_object('app.config.Config')

    # ------------------------------------------------------------------
    # налагодження та логування
    # ------------------------------------------------------------------
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
        """Виводимо повний трейсбек у консоль, повертаємо 500."""
        traceback.print_exc()
        return "Internal Server Error", 500

    # ------------------------------------------------------------------
    # реєстрація blueprint-ів
    # ------------------------------------------------------------------
    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(cashier_bp, url_prefix='/cashier')

    # ------------------------------------------------------------------
    # закриття БД після кожного запиту
    # ------------------------------------------------------------------
    @app.teardown_appcontext
    def teardown_db(exception=None):
        close_db()
    
    # ------------------------------------------------------------------
    # автоматичне застосування акцій перед кожним запитом
    # ------------------------------------------------------------------
    @app.before_request
    def _auto_apply_promos():
        # сервіс, що вмикає/вимикає акції та переоцінює товари
        from app.services.promo_service import apply_promotions
        apply_promotions()

    # ------------------------------------------------------------------
    # поточний користувач у `g`
    # ------------------------------------------------------------------
    @app.before_request
    def load_current_user():
        g.current_user = None
        if 'user_id' in session:
            conn = get_db()
            if not conn:
                # БД недоступна, пропускаємо
                return
            
            try:
                cur = conn.cursor()
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
                    # за замовчуванням виводимо username
                    full_name = row[1]
                    # якщо привʼязаний працівник — замінюємо на прізвище + ім'я
                    if row[3]:
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

                    g.current_user = type(
                        'User', (), {
                            'id':       row[0],
                            'username': row[1],
                            'name':     full_name,
                            'role':     row[2]
                        }
                    )
            except Exception as e:
                print(f"[WARNING] Error loading user: {e}")
            finally:
                close_db(conn)

    # ------------------------------------------------------------------
    # змінні доступні у всіх шаблонах
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_globals():
        return {
            'current_user': getattr(g, 'current_user', None),
            'current_year': datetime.datetime.now().year,
            'breadcrumb':   getattr(g, 'breadcrumb', None)
        }

    # ------------------------------------------------------------------
    # головна сторінка та редірект за роллю
    # ------------------------------------------------------------------
    @app.route('/')
    def index():
        if getattr(g, 'current_user', None):
            return redirect(url_for(f"{g.current_user.role}.dashboard"))
        g.breadcrumb = [('Головна', url_for('index'))]
        
        # Перевіряємо доступність БД та передаємо до шаблону
        db_status = db_available()
        return render_template('index.html', db_available=db_status)
    
    # ------------------------------------------------------------------
    # статус підключення до БД
    # ------------------------------------------------------------------
    @app.route('/db-status')
    def db_status():
        """Перевірка статусу підключення до бази даних."""
        is_available = db_available()
        return {
            'available': is_available,
            'message': 'База даних підключена' if is_available else 'База даних недоступна'
        }

    # ------------------------------------------------------------------
    # favicon.ico — уникаємо 404/500 у логах
    # ------------------------------------------------------------------
    @app.route('/favicon.ico')
    def favicon():
        """Повертає favicon або 204 No Content, якщо файл відсутній."""
        icon_path = os.path.join(
            current_app.root_path, 'static', 'img', 'favicon.ico'
        )
        if os.path.exists(icon_path):
            return send_from_directory(
                os.path.join(current_app.root_path, 'static', 'img'),
                'favicon.ico',
                mimetype='image/vnd.microsoft.icon'
            )
        return '', 204

    # ------------------------------------------------------------------
    # завершення ініціалізації
    # ------------------------------------------------------------------
    return app
