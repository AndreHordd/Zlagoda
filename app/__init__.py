from flask import Flask, render_template, session
from app.utils.auth import login_required
from app.config import Config
from app.utils.db import close_db

def create_app():
    app = Flask(
        __name__
    )
    app.config.from_object(Config)

    # закриваємо з’єднання з БД після кожного запиту
    app.teardown_appcontext(close_db)

    # реєструємо blueprint для аутентифікації
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/manager')
    @login_required(role='manager')
    def manager_page():
        return f"Менеджер: { session.get('username') }"

    @app.route('/cashier')
    @login_required(role='cashier')
    def cashier_page():
        return f"Касир: { session.get('username') }"

    return app
