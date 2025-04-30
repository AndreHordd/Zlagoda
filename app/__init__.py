import datetime
from flask import Flask, session, g, render_template, url_for, redirect
from .utils.db import get_db, close_db
from .api.auth import auth_bp
from .views.manager.routes import manager_bp
from .views.cashier.routes import cashier_bp

def create_app():
    # Явно вказуємо папки зі статикою й шаблонами
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static',
        template_folder='templates'
    )
    app.config.from_object('app.config.Config')

    # Реєструємо Blueprint-­и
    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(cashier_bp, url_prefix='/cashier')

    @app.context_processor
    def inject_globals():
        # Поточний рік для футера
        current_year = datetime.datetime.now().year

        # Поточний користувач (або None)
        user = None
        if 'user_id' in session:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT id_user, name, role
                  FROM users
                 WHERE id_user = %s
            """, (session['user_id'],))
            row = cur.fetchone()
            close_db(conn)
            if row:
                # Простий об’єкт із потрібними атрибутами
                user = type('U', (), {
                    'id':   row[0],
                    'name': row[1],
                    'role': row[2]
                })

        # Хлібні крихти для кожної сторінки
        breadcrumb = getattr(g, 'breadcrumb', None)

        return {
            'current_user': user,
            'current_year': current_year,
            'breadcrumb':   breadcrumb
        }

    @app.route('/')
    def index():
        # Якщо залогований — кидаємо відразу на його дашборд
        if g.get('current_user'):
            target = f"{g.current_user.role}.dashboard"
            return redirect(url_for(target))

        # Інакше — показуємо публічну головну
        g.breadcrumb = [('Головна', url_for('index'))]
        return render_template('index.html')

    return app
