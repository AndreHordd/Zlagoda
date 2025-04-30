from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # тут можна викликати DAO для перевірки логіну
        session['user_id']   = 'demo'
        session['user_name'] = request.form['username']
        session['user_role'] = request.form.get('role','cashier')
        return redirect(url_for(f"{session['user_role']}.dashboard"))
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        # запис у БД через DAO.create_employee(...)
        flash('Працівника створено', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
