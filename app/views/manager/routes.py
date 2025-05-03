"""
Маршрути, доступні менеджеру (URL-префікс /manager).

• /dashboard                    – дашборд
• /employees (+new /edit /delete) – повний CRUD працівників
• /customers                    – список постійних клієнтів
• /categories (+add /edit /delete)   – список + CRUD категорій
• /products                     – типи товарів + CRUD
• /store_products               – товари у магазині + CRUD
• /reports                      – сторінка звітів
• /reports/preview/<table>      – HTML-фрагмент для попереднього перегляду
• /receipts                     – список чеків з фільтром за періодом
• /receipt/<check_number>       – деталі одного чека
• /statistics                   – загальна статистика продажів
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort
)
from psycopg.errors import ForeignKeyViolation

from app.dao.report_dao import categories_sold_by_cashier, category_price_stats, cashiers_every_check_has_category, \
    categories_without_promos
from app.dao.sale_dao import delete_sale
from app.utils.auth import ensure_role
from app.dao.category_dao import get_all_categories
from app.dao.product_dao import get_all_product_types

# ─── DAO ────────────────────────────────────────────────────────────
# працівники
from app.dao.employee_dao import (
    get_all_employees,
    get_employee_by_id,
    create_employee,
    update_employee,
    delete_employee_by_id
)
# постійні клієнти (менеджер)
from app.dao.customer_card_dao import get_all_customers_m, delete_card, update_card, create_card, generate_card_number
# категорії
from app.dao.category_dao import (
    get_all_categories,
    create_category,
    update_category,
    delete_category
)
# типи товарів
from app.dao.product_dao import (
    get_all_product_types,
    get_product_type_by_id,
    create_product_type,
    update_product_type,
    delete_product_type,
    get_all_products               # for listings in dashboard/statistics
)
# товари у магазині (CRUD by UPC)
from app.dao.store_product_dao import (
    create_store_product,
    get_store_product_by_upc,
    update_store_product,
    delete_store_product as dao_delete_store_product, generate_upc, get_all_store_products
)
# щоб view-функція могла називатися get_store_product
get_store_product = get_store_product_by_upc

# чеки / статистика
from app.dao.check_dao import (
    get_check_details,
    get_checks_all_period,
    get_checks_by_employee_period_mgr,
    get_total_sales_by_cashier_period,
    get_total_sales_all_period,
    get_quantity_sold_period, delete_check
)


manager_bp = Blueprint('manager', __name__, url_prefix='/manager')


@manager_bp.before_request
def _restrict_manager():
    return ensure_role('manager')


# ═══════════════ 1. DASHBOARD ═══════════════
@manager_bp.route('/dashboard')
def dashboard():
    employees   = get_all_employees()
    num_total   = len(employees)
    num_cashier = len([e for e in employees if e['role']=='cashier'])
    num_mgr     = len([e for e in employees if e['role']=='manager'])

    products      = get_all_products()          # товари в магазині
    prod_in_store = len(products)

    prod_types = len(get_all_product_types())

    today    = date.today()
    last_30  = today - timedelta(days=29)
    sales_30 = get_total_sales_all_period(last_30, today) or Decimal('0')

    # TOP-5 за 30 днів
    top = []
    for p in products:
        qty = get_quantity_sold_period(p['upc'], last_30, today)
        if qty:
            top.append((qty, p))
    top = sorted(top, reverse=True)[:5]

    return render_template(
        'manager/dashboard.html',
        num_total=num_total,
        num_cashier=num_cashier,
        num_mgr=num_mgr,
        prod_types=prod_types,
        prod_in_store=prod_in_store,
        sales_30=sales_30,
        top_products=top,
        today=today.isoformat()
    )


# ═══════════════ 2. ПРАЦІВНИКИ ═══════════════
@manager_bp.route('/employees')
def employees():
    sort_by       = request.args.get('sort_by','surname')
    order         = request.args.get('order','asc')
    role_filter   = request.args.get('role')
    if role_filter not in ('manager','cashier'):
        role_filter = None
    search_filter = request.args.get('search','').strip() or None

    emps = get_all_employees(sort_by, order,
                             role_filter, search_filter)
    return render_template(
        'manager/employees.html',
        employees=emps,
        sort_by=sort_by, order=order,
        role_filter=role_filter,
        search_filter=search_filter
    )


@manager_bp.route('/employees/new', methods=('GET','POST'))
def new_employee():
    if request.method=='POST':
        try:
            create_employee(
                request.form['surname'],
                request.form['name'],
                request.form.get('patronymic') or None,
                request.form['role'],
                float(request.form['salary']),
                request.form['dob'],
                request.form['start_date'],
                request.form['phone'],
                request.form['city'],
                request.form['street'],
                request.form['zip_code']
            )
            flash('Працівника створено.','success')
            return redirect(url_for('manager.employees'))
        except ValueError:
            flash('Невірний формат числових полів.','danger')
        except Exception as e:
            flash(f'Помилка: {e}','danger')
    return render_template(
        'manager/employee_form.html',
        mode='new', employee={}
    )


@manager_bp.route('/employees/edit/<emp_id>', methods=('GET','POST'))
def edit_employee(emp_id):
    emp = get_employee_by_id(emp_id)
    if not emp:
        flash('Працівника не знайдено.','danger')
        return redirect(url_for('manager.employees'))
    if request.method=='POST':
        try:
            update_employee(
                emp_id,
                request.form['surname'],
                request.form['name'],
                request.form.get('patronymic') or None,
                request.form['role'],
                float(request.form['salary']),
                request.form['dob'],
                request.form['start_date'],
                request.form['phone'],
                request.form['city'],
                request.form['street'],
                request.form['zip_code']
            )
            flash('Дані оновлено.','success')
            return redirect(url_for('manager.employees'))
        except ValueError:
            flash('Невірний формат числових полів.','danger')
        except Exception as e:
            flash(f'Помилка: {e}','danger')
    return render_template(
        'manager/employee_form.html',
        mode='edit', employee=emp
    )


@manager_bp.route('/employees/delete/<emp_id>', methods=('POST',))
def delete_employee(emp_id):
    if delete_employee_by_id(emp_id):
        flash('Працівника видалено.','success')
    else:
        flash('Не вдалося видалити.','danger')
    return redirect(url_for('manager.employees'))


# ═══════════════ 3. ПОСТІЙНІ КЛІЄНТИ ═══════════════
@manager_bp.route('/customers')
def customers():
    sort_by      = request.args.get('sort_by','surname')
    order        = request.args.get('order','asc')
    search       = request.args.get('search','').strip() or None

    # читаємо нові параметри
    try:
        min_p = request.args.get('min_percent')
        min_percent = int(min_p) if min_p not in (None,'') else None
    except ValueError:
        min_percent = None

    try:
        max_p = request.args.get('max_percent')
        max_percent = int(max_p) if max_p not in (None,'') else None
    except ValueError:
        max_percent = None

    customers = get_all_customers_m(
        sort_by=sort_by,
        order=order,
        min_percent=min_percent,
        max_percent=max_percent,
        search=search
    )
    return render_template(
        'manager/customers.html',
        customers=customers,
        sort_by=sort_by,
        order=order,
        search_filter=search,
        min_percent=min_percent,
        max_percent=max_percent
    )


# app/views/manager/routes.py

@manager_bp.route('/customers/new', methods=('GET','POST'))
def new_customer():
    if request.method == 'POST':
        # Зчитуємо всі поля на вході
        surname    = request.form.get('surname','').strip()
        name       = request.form.get('name','').strip()
        phone      = request.form.get('phone','').strip()
        percent_raw= request.form.get('percent','').strip()
        # інші необов’язкові
        patronymic = request.form.get('patronymic') or None
        city       = request.form.get('city') or None
        street     = request.form.get('street') or None
        zip_code   = request.form.get('zip_code') or None

        # 1) Перевірка обов’язкових полів
        if not surname or not name or not phone or not percent_raw:
            flash('Поля Прізвище, Ім’я, Телефон та Знижка є обов’язковими.', 'warning')
            return render_template('manager/customer_form.html',
                                   mode='new',
                                   customer=request.form)

        # 2) Перевірка формату знижки
        try:
            percent = int(percent_raw)
            if not (0 <= percent <= 100):
                raise ValueError
        except ValueError:
            flash('Знижка повинна бути числом від 0 до 100.', 'danger')
            return render_template('manager/customer_form.html',
                                   mode='new',
                                   customer=request.form)

        # 3) Створюємо картку
        try:
            card_num = generate_card_number()
            create_card(card_num,
                        surname, name, patronymic,
                        phone, city, street, zip_code,
                        percent)
            flash(f'Клієнт створений (№ картки: {card_num}).', 'success')
            return redirect(url_for('manager.customers'))
        except Exception as e:
            flash(f'Помилка БД: {e}', 'danger')

    # GET
    return render_template('manager/customer_form.html',
                           mode='new',
                           customer={})


@manager_bp.route('/customers/edit/<card_number>', methods=('GET','POST'))
def edit_customer(card_number):
    # витягуємо існуючі дані
    cust = next((c for c in get_all_customers_m() if c['card_number']==card_number), None)
    if not cust:
        flash('Клієнта не знайдено.', 'danger')
        return redirect(url_for('manager.customers'))

    if request.method == 'POST':
        surname    = request.form.get('surname','').strip()
        name       = request.form.get('name','').strip()
        phone      = request.form.get('phone','').strip()
        percent_raw= request.form.get('percent','').strip()
        patronymic = request.form.get('patronymic') or None
        city       = request.form.get('city') or None
        street     = request.form.get('street') or None
        zip_code   = request.form.get('zip_code') or None

        # Перевірка обов’язкових полів
        if not surname or not name or not phone or not percent_raw:
            flash('Поля Прізвище, Ім’я, Телефон та Знижка є обов’язковими.', 'warning')
            return render_template('manager/customer_form.html',
                                   mode='edit',
                                   customer=request.form)

        # Перевірка формату знижки
        try:
            percent = int(percent_raw)
            if not (0 <= percent <= 100):
                raise ValueError
        except ValueError:
            flash('Знижка повинна бути числом від 0 до 100.', 'danger')
            return render_template('manager/customer_form.html',
                                   mode='edit',
                                   customer=request.form)

        # Оновлюємо записи
        try:
            ok = update_card(card_number,
                             surname, name, patronymic,
                             phone, city, street, zip_code,
                             percent)
            flash('Дані клієнта оновлено.' if ok else 'Нічого не змінено.', 'success')
            return redirect(url_for('manager.customers'))
        except Exception as e:
            flash(f'Помилка БД: {e}', 'danger')

    # GET
    return render_template('manager/customer_form.html',
                           mode='edit',
                           customer=cust)


@manager_bp.route('/customers/delete/<card_number>', methods=('POST',))
def delete_customer(card_number):
    try:
        ok = delete_card(card_number)
        flash('Клієнта видалено', 'success' if ok else 'warning')
    except ForeignKeyViolation:
        flash('Неможливо видалити — на клієнта є записи в чеках', 'danger')
    except Exception as e:
        flash(f'Помилка БД: {e}', 'danger')
    return redirect(url_for('manager.customers'))
# ═══════════════ 4. КАТЕГОРІЇ ═══════════════
@manager_bp.route('/categories', methods=('GET','POST'))
def categories():
    if request.method=='POST':
        name = request.form.get('new_name','').strip()
        if not name:
            flash('Назва не може бути порожньою.','warning')
        else:
            try:
                create_category(name)
                flash('Категорію додано.','success')
            except Exception as e:
                flash(f'Помилка: {e}','danger')
        return redirect(url_for('manager.categories'))

    sort_by = request.args.get('sort_by','name')
    order   = request.args.get('order','asc')
    cats    = get_all_categories(sort_by, order)
    return render_template(
        'manager/categories.html',
        categories=cats,
        sort_by=sort_by,
        order=order
    )


@manager_bp.route('/categories/edit/<int:cat_id>', methods=('GET','POST'))
def edit_category(cat_id):
    cat = next((c for c in get_all_categories() if c['id']==cat_id), None)
    if not cat:
        flash('Категорію не знайдено.','danger')
        return redirect(url_for('manager.categories'))
    if request.method=='POST':
        new_name = request.form['name_category'].strip()
        if not new_name:
            flash('Назва не може бути порожньою.','warning')
        else:
            try:
                update_category(cat_id, new_name)
                flash('Категорію оновлено.','success')
                return redirect(url_for('manager.categories'))
            except Exception as e:
                flash(f'Помилка: {e}','danger')
    return render_template(
        'manager/categories_form.html',
        mode='edit', category=cat
    )


@manager_bp.route('/categories/delete/<int:cat_id>', methods=('POST',))
def delete_category_route(cat_id):
    try:
        deleted = delete_category(cat_id)
        if deleted:
            flash('Категорію видалено.', 'success')
        else:
            flash('Не вдалося видалити категорію.', 'danger')
    except ForeignKeyViolation:
        flash(
            'Неможливо видалити категорію — у базі є товари цієї категорії.',
            'danger'
        )
    except Exception as e:
        flash(f'Невідома помилка при видаленні: {e}', 'danger')
    return redirect(url_for('manager.categories'))


# ═══════════════ 5. ТИПИ ТОВАРІВ (CRUD) ═══════════════
from app.dao.product_type_dao import (
    create_product_type,
    get_all_product_types,
    get_product_type_by_id,
    update_product_type,
    delete_product_type
)
@manager_bp.route('/products')
def products():
    # 1) Зчитуємо параметри з рядка запиту
    sort_by  = request.args.get('sort_by', 'name')
    order    = request.args.get('order',   'asc')
    category = request.args.get('category') or None
    search   = request.args.get('search', '').strip() or None

    # 2) Викликаємо DAO із цими параметрами
    types = get_all_product_types(sort_by, order, category, search)

    # 3) Підтягуємо список категорій для фільтра
    cats = [c['name'] for c in get_all_categories()]

    # 4) Передаємо все в шаблон
    return render_template(
        'manager/product_types.html',
        product_types=types,
        categories=cats,
        sort_by=sort_by,
        order=order,
        category=category,
        search=search
    )


@manager_bp.route('/products/new', methods=('GET','POST'))
def new_product_type():
    cats = [c['name'] for c in get_all_categories()]
    if request.method=='POST':
        name     = request.form['name'].strip()
        category = request.form['category'].strip()
        if not name:
            flash('Назва не може бути порожньою.', 'warning')
        elif category not in cats:
            flash(f'Категорії «{category}» не існує.', 'danger')
        else:
            try:
                create_product_type(name, category)
                flash('Тип товару створено.', 'success')
                return redirect(url_for('manager.products'))
            except Exception as e:
                flash(f'Помилка БД: {e}', 'danger')
    return render_template(
        'manager/products_form.html',
        mode='new',
        product_type={},  # пустий для шаблону
        categories=cats
    )

@manager_bp.route('/products/edit/<int:pt_id>', methods=('GET','POST'))
def edit_product_type(pt_id):
    cats = [c['name'] for c in get_all_categories()]
    pt = get_product_type_by_id(pt_id)
    if not pt:
        flash('Тип товару не знайдено.', 'danger')
        return redirect(url_for('manager.products'))
    if request.method=='POST':
        name     = request.form['name'].strip()
        category = request.form['category'].strip()
        if not name:
            flash('Назва не може бути порожньою.', 'warning')
        elif category not in cats:
            flash(f'Категорії «{category}» не існує.', 'danger')
        else:
            try:
                update_product_type(pt_id, name, category)
                flash('Дані оновлено.', 'success')
                return redirect(url_for('manager.products'))
            except Exception as e:
                flash(f'Помилка БД: {e}', 'danger')
    return render_template(
        'manager/products_form.html',
        mode='edit',
        product_type=pt,
        categories=cats
    )

@manager_bp.route('/products/delete/<int:pt_id>', methods=('POST',))
def delete_product_type_route(pt_id):
    if delete_product_type(pt_id):
        flash('Тип товару видалено.', 'success')
    else:
        flash('Не вдалося видалити.', 'danger')
    return redirect(url_for('manager.products'))

# ═══════════════ 6. ТОВАРИ У МАГАЗИНІ (CRUD) ═══════════════

@manager_bp.route('/store_products')
def store_products():
    # Параметри сортування/фільтрів з request.args…
    sort_by    = request.args.get('sort_by','quantity')
    order      = request.args.get('order','desc')
    category   = request.args.get('category') or None
    promo      = request.args.get('promo')               # '', '1', '0'
    promotional= {'1':True,'0':False}.get(promo, None)
    field      = request.args.get('field','name')
    search     = request.args.get('search','').strip() or None

    items = get_all_products(
        sort_by, order,
        category, promotional,
        search, field
    )
    cats = get_all_categories()
    return render_template(
        'manager/store_products.html',
        store_products=items,
        categories=cats,
        sort_by=sort_by, order=order,
        category=category, promo=promo,
        field=field, search=search
    )
@manager_bp.route('/store_products/new', methods=('GET', 'POST'))
def new_store_product():
    """
    Створює новий товар у магазині з автоматично згенерованим UPC та UPC_prom=NULL.
    Форми очікують лише вибір типу товару, ціну, кількість та дату закінчення.
    """
    categories    = get_all_categories()
    product_types = get_all_product_types()

    if request.method == 'POST':
        try:
            # Зчитуємо дані з форми
            product_id  = int(request.form['product_id'])
            price       = float(request.form['price'])
            quantity    = int(request.form['quantity'])
            expiry_date = request.form['expiry_date']  # формат 'YYYY-MM-DD'

            # Створюємо запис у БД
            ok, upc = create_store_product(
                product_id,
                price,
                quantity,
                expiry_date
            )

            if ok:
                flash(f'Товар успішно створено. UPC={upc}.', 'success')
            else:
                flash('Не вдалося додати товар.', 'danger')

            return redirect(url_for('manager.store_products'))

        except KeyError as e:
            flash(f'Відсутнє поле у формі: {e.args[0]}', 'danger')
        except ValueError:
            flash('Невірний формат числового поля.', 'danger')
        except Exception as e:
            flash(f'Помилка при створенні товару: {e}', 'danger')

    # GET-запит: рендеримо порожню форму
    return render_template(
        'manager/store_product_form.html',
        mode='new',
        categories=categories,
        product_types=product_types,
        product={}  # у шаблоні fields default('') забезпечить пусті інпути
    )


@manager_bp.route('/store_products/edit/<string:upc>', methods=('GET','POST'))
def edit_store_product(upc):
    item = get_store_product_by_upc(upc)
    if not item:
        abort(404)
    categories   = get_all_categories()
    product_types = get_all_product_types()
    if request.method == 'POST':
        try:
            product_id  = int(request.form['product_id'])
            price       = float(request.form['price'])
            quantity    = int(request.form['quantity'])
            expiry_date = request.form['expiry_date']

            ok = update_store_product(
                upc, product_id, price, quantity, expiry_date
            )
            flash('Дані оновлено.' if ok else 'Не вдалося оновити.',
                  'success' if ok else 'danger')
            return redirect(url_for('manager.store_products'))
        except KeyError as e:
            flash(f'Відсутнє поле: {e.args[0]}', 'danger')
        except ValueError:
            flash('Невірний формат числа.', 'danger')
        except Exception as e:
            flash(f'Помилка БД: {e}', 'danger')
    return render_template(
        'manager/store_product_form.html',
        mode='edit',
        categories=categories,
        product_types=product_types,
        product=item
    )


@manager_bp.route('/store_products/delete/<string:upc>', methods=('POST',))
def delete_store_product_route(upc):
    success = dao_delete_store_product(upc)
    flash(
        'Товар видалено.' if success else 'Товар не знайдено.',
        'success' if success else 'warning'
    )
    return redirect(url_for('manager.store_products'))
# ═══════════════ 7. PREVIEW для звітів ═══════════════
@manager_bp.route('/reports/preview/<table>')
def reports_preview(table):
    mapping = {
        'employees':      lambda: get_all_employees('surname','asc'),
        'customers':      get_all_customers_m,
        'categories':     get_all_categories,
        'product_types':  lambda: get_all_product_types('name','asc'),
        'store_products': lambda: get_all_products('quantity','desc')
    }
    if table not in mapping:
        abort(404)
    data = mapping[table]()
    return render_template(
        f'manager/report_tables/{table}.html',
        data=data, today=date.today()
    )


# ═══════════════ 8. Сторінка звітів ═══════════════
@manager_bp.route('/reports')
def reports():
    return render_template('manager/reports.html')


# ═══════════════ 9. ЧЕКИ З ПЕРІОДОМ ═══════════════
@manager_bp.route('/receipts')
def receipts():
    period  = request.args.get('period','day')
    ref_day = request.args.get('date','')

    if period=='all':
        d_from = d_to = None
    else:
        try:
            ref = datetime.strptime(ref_day,"%Y-%m-%d").date()
        except:
            ref = date.today()
        spans = {'day':1,'7d':7,'month':30,'year':365}
        if period in spans:
            d_to   = ref
            d_from = ref - timedelta(days=spans[period]-1)
        else:
            try: d_from = datetime.strptime(request.args.get('from',''),"%Y-%m-%d").date()
            except: d_from = None
            try: d_to   = datetime.strptime(request.args.get('to',''),  "%Y-%m-%d").date()
            except: d_to   = None

    sort_by = request.args.get('sort_by','date')
    order   = request.args.get('order','desc')

    receipts = get_checks_all_period(d_from, d_to, sort_by, order)

    return render_template(
        'manager/receipts.html',
        receipts=receipts,
        period=period,
        ref_day=ref.isoformat() if period!='all' else '',
        d_from=d_from.isoformat() if d_from else '',
        d_to=d_to.isoformat()     if d_to   else '',
        sort_by=sort_by, order=order
    )


@manager_bp.route('/receipt/<check_number>')
def receipt_detail_mgr(check_number):
    details = get_check_details(check_number)
    if not details:
        abort(404)
    return render_template('cashier/receipt_detail.html', **details)

# ═══════════════ Видалення продажу (рядка) ═══════════════
@manager_bp.route('/receipts/<check_number>/sale/delete/<upc>', methods=('POST',))
def delete_sale_route(check_number, upc):
    success = delete_sale(upc, check_number)
    if success:
        flash(f'Продаж UPC={upc} у чеку {check_number} видалено.', 'success')
    else:
        flash('Не вдалося видалити продаж (такого запису немає).', 'danger')
    return redirect(url_for('manager.receipt_detail_mgr', check_number=check_number))

# ═══════════════ Видалення чека ═══════════════
@manager_bp.route('/receipts/delete/<check_number>', methods=('POST',))
def delete_check_route(check_number):
    # перевіримо спочатку, чи такий чек є
    from app.dao.check_dao import get_check_details
    if not get_check_details(check_number):
        flash('Чек не знайдено.', 'danger')
        return redirect(url_for('manager.receipts'))

    success = delete_check(check_number)
    if success:
        flash(f'Чек {check_number} успішно видалено (разом із продажами).', 'success')
    else:
        flash('Не вдалося видалити чек.', 'danger')
    return redirect(url_for('manager.receipts'))


# app/views/manager/routes.py

from app.dao.check_dao import (
    get_checks_all_period,
    delete_check,
    # ... інші імпорти
)

# app/views/manager/routes.py

@manager_bp.route('/receipts/delete/<check_number>', methods=('POST',))
def delete_receipt(check_number):
    # Забираємо фільтри з форми
    period    = request.form.get('period', 'day')
    date_from = request.form.get('from',   '')
    date_to   = request.form.get('to',     '')
    sort_by   = request.form.get('sort_by','date')
    order     = request.form.get('order',  'desc')

    try:
        if delete_check(check_number):
            flash(f'Чек {check_number} успішно видалено.', 'success')
        else:
            flash(f'Чек {check_number} не знайдено.', 'warning')
    except Exception as e:
        flash(f'Помилка при видаленні чека: {e}', 'danger')

    # Редірект на список з тими ж фільтрами
    return redirect(url_for(
        'manager.receipts',
        period=period,
        **{
            'from':    date_from,
            'to':      date_to,
            'sort_by': sort_by,
            'order':   order
        }
    ))

# ═══════════════ 10. СТАТИСТИКА ═══════════════
@manager_bp.route('/statistics')
def statistics():
    cashiers = [e for e in get_all_employees() if e['role']=='cashier']

    cashier_id = request.args.get('cashier')
    if cashier_id in (None,'all'):
        cashier_id = None

    period     = request.args.get('period','day')
    ref_day    = request.args.get('date','')
    upc_or_name = request.args.get('product') or None

    if period=='all':
        d_from = d_to = None
    else:
        try:
            ref = datetime.strptime(ref_day,"%Y-%m-%d").date()
        except:
            ref = date.today()
        spans = {'day':1,'7d':7,'month':30,'year':365}
        if period in spans:
            d_to   = ref
            d_from = ref - timedelta(days=spans[period]-1)
        else:
            try: d_from = datetime.strptime(request.args.get('from',''),"%Y-%m-%d").date()
            except: d_from = None
            try: d_to   = datetime.strptime(request.args.get('to',''),  "%Y-%m-%d").date()
            except: d_to   = None

    total_all        = get_total_sales_all_period(d_from, d_to)
    total_by_cashier = None
    if cashier_id:
        total_by_cashier = get_total_sales_by_cashier_period(
            cashier_id, d_from, d_to
        )

    chosen_product = None
    qty_sold       = None
    if upc_or_name:
        lst = get_all_products(search=upc_or_name, search_field='upc')
        if not lst:
            lst = get_all_products(search=upc_or_name, search_field='name')
        if lst:
            chosen_product = lst[0]
            qty_sold = get_quantity_sold_period(
                chosen_product['upc'], d_from, d_to
            )

    products_for_js = get_all_products(sort_by='name', order='asc')

    rows = categories_sold_by_cashier()


    price_table = category_price_stats(min_units=50)
    loyal_cashiers = cashiers_every_check_has_category('Молочні')
    rare_cats = categories_without_promos(big_stock=100)

    return render_template(
        'manager/statistics.html',
        cashiers=cashiers,
        cashier_id=cashier_id,
        period=period,
        ref_day=ref.isoformat() if period != 'all' else '',
        d_from=d_from.isoformat() if d_from else '',
        d_to=d_to.isoformat() if d_to else '',
        product_input=upc_or_name,
        total_all=total_all,
        total_by_cashier=total_by_cashier,
        qty_sold=qty_sold,
        chosen_product=chosen_product,
        products=products_for_js,
        # ↓↓↓ передаємо у шаблон нові таблиці
        price_table=price_table[:5],
        loyal_cashiers=loyal_cashiers[:5],
        rare_cats=rare_cats,
        cashier_stats=rows
    )


