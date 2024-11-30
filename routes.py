from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Medication, Consumption, InventoryLog
from forms import MedicationForm, ConsumptionForm, InventoryUpdateForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    consumption_form = ConsumptionForm()
    return render_template('dashboard.html', 
                         medications=medications,
                         consumption_form=consumption_form)

@main_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    form = MedicationForm()
    update_form = InventoryUpdateForm()
    
    if form.validate_on_submit():
        medication = Medication(
            name=form.name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            current_stock=form.current_stock.data,
            user_id=current_user.id
        )
        db.session.add(medication)
        db.session.commit()
        
        # Create initial inventory log
        inventory_log = InventoryLog(
            medication_id=medication.id,
            quantity_change=form.current_stock.data,
            operation_type='add'
        )
        db.session.add(inventory_log)
        db.session.commit()
        
        flash('Medication added successfully!', 'success')
        return redirect(url_for('main.inventory'))
    
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    return render_template('inventory.html', 
                         form=form,
                         update_form=update_form,
                         medications=medications)

@main_bp.route('/update_stock/<int:med_id>', methods=['POST'])
@login_required
def update_stock(med_id):
    form = InventoryUpdateForm()
    if form.validate_on_submit():
        medication = Medication.query.get_or_404(med_id)
        if medication.user_id != current_user.id:
            flash('Unauthorized access!', 'danger')
            return redirect(url_for('main.inventory'))
            
        quantity_change = form.quantity.data
        medication.current_stock += quantity_change
        
        inventory_log = InventoryLog(
            medication_id=med_id,
            quantity_change=quantity_change,
            operation_type='add' if quantity_change > 0 else 'remove'
        )
        
        db.session.add(inventory_log)
        db.session.commit()
        flash('Stock updated successfully!', 'success')
    return redirect(url_for('main.inventory'))

@main_bp.route('/log_consumption/<int:med_id>', methods=['POST'])
@login_required
def log_consumption(med_id):
    form = ConsumptionForm()
    if form.validate_on_submit():
        medication = Medication.query.get_or_404(med_id)
        if medication.current_stock >= form.quantity.data:
            consumption = Consumption(
                medication_id=med_id,
                quantity=form.quantity.data
            )
            medication.current_stock -= form.quantity.data
            
            inventory_log = InventoryLog(
                medication_id=med_id,
                quantity_change=-form.quantity.data,
                operation_type='remove'
            )
            
            db.session.add(consumption)
            db.session.add(inventory_log)
            db.session.commit()
            flash('Consumption logged successfully!', 'success')
        else:
            flash('Insufficient stock!', 'danger')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/history')
@login_required
def history():
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', medications=medications)
