from flask import Blueprint, render_template

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
def dashboard():
    return render_template('manager/dashboard.html')

@manager_bp.route('/employees')
def employees():
    # employees = employee_dao.get_all_employees()
    return render_template('manager/employees.html', employees=[])
