"""
Маршрути для ролі 'cashier'.
"""

from datetime   import date, datetime, timedelta
from flask      import (
    Blueprint, render_template, session,
    redirect, url_for, flash, request
)
from app.utils.auth            import ensure_role
from app.dao.product_dao       import (
    get_all_products, get_all_product_types
)
from app.dao.category_dao      import get_all_categories
from app.dao.check_dao         import (
    get_checks_by_employee, get_checks_by_employee_period
)
from app.dao.employee_dao      import get_employee_by_id

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')

# підблюпрінти
from .customer import cashier_cards_bp           # noqa: E402
cashier_bp.register_blueprint(cashier_cards_bp)
from . import check                              # noqa: E402

# ───────────────────────── захист ролі ──────────────────────────
@cashier_bp.before_request
def _restrict_cashier():
    return ensure_role('cashier')


# ───────────────────────── ДАШБОРД ──────────────────────────────
@cashier_bp.route('/dashboard')
def dashboard():
    # отримуємо id поточного працівника з сесії
    emp_id = session.get('employee_id')
    if not emp_id:
        flash('Неможливо отримати профіль: сесія не містить employee_id', 'danger')
        return redirect(url_for('auth.login'))

    # дані працівника
    emp = get_employee_by_id(emp_id)

    # всі товари в магазині
    items = get_all_products()
    available_count = len(items)

    return render_template(
        'cashier/dashboard.html',
        employee=emp,
        available_count=available_count
    )


# ─────────────────────  ТОВАРИ в магазині  ──────────────────────
@cashier_bp.route('/products')
def products():
    sort_by = request.args.get('sort_by', 'name')
    order   = request.args.get('order',   'asc')

    category = request.args.get('category') or None
    promo    = request.args.get('promo')            # '', '1', '0'
    search   = request.args.get('search', '').strip() or None
    field    = request.args.get('field', 'name')
    if field not in ('name', 'upc'):
        field = 'name'

    promotional = {'1': True, '0': False}.get(promo, None)

    store_products = get_all_products(
        sort_by, order,
        category, promotional,
        search, field
    )
    categories = get_all_categories()

    return render_template(
        'cashier/products.html',
        store_products=store_products,
        sort_by=sort_by, order=order,
        category=category, promo=promo,
        search=search, field=field,
        categories=categories
    )


# ─────────────────────  ТИПИ ТОВАРІВ  ───────────────────────────
@cashier_bp.route('/product_types')
def product_types():
    sort_by  = request.args.get('sort_by', 'name')
    order    = request.args.get('order', 'asc')
    category = request.args.get('category') or None
    search   = request.args.get('search', '').strip() or None

    types      = get_all_product_types(sort_by, order, category, search)
    categories = get_all_categories()

    return render_template(
        'cashier/product_types.html',
        product_types=types,
        sort_by=sort_by, order=order,
        category=category, search=search,
        categories=categories
    )


# ─────────────────────  МОЇ ЧЕКИ  ───────────────────────────────
@cashier_bp.route('/my_receipts')
def my_receipts():
    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Неможливо отримати чеки: невідомий касир', 'danger')
        return redirect(url_for('auth.login'))

    # 1) Параметри фільтрації періоду
    period  = request.args.get('period', 'day')   # day|7d|month|year|all|custom
    ref_day = request.args.get('date')            # YYYY-MM-DD

    # 2) Обчислюємо d_from та d_to відповідно до period
    if period == 'all':
        d_from = d_to = None
    else:
        try:
            ref = datetime.strptime(ref_day, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            ref = date.today()
        spans = {'day':1, '7d':7, 'month':30, 'year':365}
        if period in spans:
            d_to   = ref
            d_from = ref - timedelta(days=spans[period]-1)
        else:  # custom
            try:
                d_from = datetime.strptime(request.args.get('from',''), "%Y-%m-%d").date()
            except (TypeError, ValueError):
                d_from = None
            try:
                d_to   = datetime.strptime(request.args.get('to',''),   "%Y-%m-%d").date()
            except (TypeError, ValueError):
                d_to = None

    # 3) Сортування
    sort_by = request.args.get('sort_by', 'date')
    order   = request.args.get('order',   'desc')

    # 4) Вибір DAO
    if d_from or d_to:
        receipts = get_checks_by_employee_period(
            employee_id, d_from, d_to, sort_by, order
        )
    else:
        receipts = get_checks_by_employee(
            employee_id, sort_by, order
        )

    # 5) Рендеримо шаблон, передаючи саме ті змінні, що чекає ваш HTML
    return render_template(
        'cashier/my_receipts.html',
        receipts=receipts,
        period=period,
        date_from=d_from.isoformat() if d_from else '',
        date_to  =d_to.isoformat()   if d_to   else '',
        sort_by=sort_by,
        order=order
    )