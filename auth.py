from flask import Blueprint, render_template, redirect, url_for, flash, request
from urllib.parse import urlparse as url_parse
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegistrationForm
from models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to dashboard if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    password_hash=generate_password_hash(form.password.data)
                )
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred during registration. Please try again.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to dashboard if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(email=form.email.data).first()
                if user and check_password_hash(user.password_hash, form.password.data):
                    login_user(user, remember=form.remember_me.data)
                    next_page = request.args.get('next')
                    if not next_page or url_parse(next_page).netloc != '':
                        next_page = url_for('main.dashboard')
                    flash('Login successful!', 'success')
                    return redirect(next_page)
                flash('Invalid email or password', 'danger')
            except Exception as e:
                flash('An error occurred during login. Please try again.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
