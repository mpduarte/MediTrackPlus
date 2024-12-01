from flask import Blueprint, render_template, redirect, url_for, flash, request
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from forms import LoginForm, RegistrationForm, MedicationForm, InventoryUpdateForm, ConsumptionForm, PrescriptionForm
from models import Medication, InventoryLog, Consumption, Prescription
from app import db
import os
from flask_login import login_required, current_user
from app import db
from models import Medication, Consumption, InventoryLog
from forms import MedicationForm, ConsumptionForm, InventoryUpdateForm
import logging
import os
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Configure upload folder
UPLOAD_FOLDER = 'static/uploads/prescriptions'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    medications_dict = [med.to_dict() for med in medications]
    consumption_form = ConsumptionForm()
    return render_template('dashboard.html', 
                         medications=medications_dict,
                         consumption_form=consumption_form)

@main_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    form = MedicationForm()
    update_form = InventoryUpdateForm()
    
    if form.validate_on_submit():
        logger.debug(f"Form validated successfully. Processing medication addition for user {current_user.id}")
        try:
            medication = Medication(
                name=form.name.data,
                dosage=form.dosage.data,
                frequency=form.frequency.data,
                current_stock=form.current_stock.data,
                scheduled_time=form.scheduled_time.data,
                max_daily_doses=form.max_daily_doses.data,
                user_id=current_user.id
            )
            logger.debug(f"Created medication object: {medication.name}")
            
            db.session.add(medication)
            logger.debug("Added medication to session")
            
            db.session.flush()  # Get the medication ID before committing
            
            # Create initial inventory log
            inventory_log = InventoryLog(
                medication_id=medication.id,
                quantity_change=form.current_stock.data,
                operation_type='add'
            )
            db.session.add(inventory_log)
            logger.debug("Added inventory log to session")
            
            db.session.commit()
            logger.info(f"Successfully added medication {medication.name} for user {current_user.id}")
            flash('Medication added successfully!', 'success')
            return redirect(url_for('main.inventory'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding medication: {str(e)}")
            flash('An error occurred while adding the medication. Please try again.', 'danger')
    else:
        if form.errors:
            logger.warning(f"Form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    try:
        medications = Medication.query.filter_by(user_id=current_user.id).order_by(Medication.name).all()
        logger.debug(f"Retrieved {len(medications)} medications for user {current_user.id}")
    except Exception as e:
        logger.error(f"Error retrieving medications: {str(e)}")
        medications = []
        flash('Error loading medications. Please try again.', 'danger')
    
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

@main_bp.route('/upload_prescription/<int:med_id>', methods=['GET', 'POST'])
@login_required
def upload_prescription(med_id):
    medication = Medication.query.get_or_404(med_id)
    if medication.user_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('main.inventory'))
    
    form = PrescriptionForm()
    if form.validate_on_submit():
        try:
            file = form.prescription_file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                
                prescription = Prescription(
                    medication_id=med_id,
                    file_name=filename,
                    file_path=file_path,
                    expiry_date=form.expiry_date.data,
                    notes=form.notes.data
                )
                
                db.session.add(prescription)
                db.session.commit()
                flash('Prescription uploaded successfully!', 'success')
                return redirect(url_for('main.inventory'))
            else:
                flash('Invalid file type. Please upload a PDF or image file.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error uploading prescription: {str(e)}")
            flash('An error occurred while uploading the prescription.', 'danger')
    
    return render_template('upload_prescription.html', form=form, medication=medication)

@main_bp.route('/history')
@login_required
def history():
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', medications=medications)

@main_bp.route('/medication/<int:med_id>/delete', methods=['POST'])
@login_required
def delete_medication(med_id):
    medication = Medication.query.filter_by(id=med_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(medication)
        db.session.commit()
        flash('Medication deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the medication', 'danger')
    return redirect(url_for('main.inventory'))


@main_bp.route('/reports')
@login_required
def reports():
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Get filter parameters
    date_range = request.args.get('date_range', '7')
    medication_id = request.args.get('medication_id', '')
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=int(date_range))
    
    # Base query for consumption records
    query = db.session.query(Consumption).join(Medication).\
        filter(Medication.user_id == current_user.id).\
        filter(Consumption.taken_at >= start_date)
    
    if medication_id:
        query = query.filter(Medication.id == medication_id)
    
    # Get consumption records
    consumption_records = query.order_by(Consumption.taken_at.desc()).all()
    
    # Calculate summary statistics
    total_consumption = sum(record.quantity for record in consumption_records)
    
    # Calculate adherence rate
    adherence_rate = 0
    if consumption_records:
        taken_count = len([r for r in consumption_records if r.status == 'taken'])
        adherence_rate = (taken_count / len(consumption_records)) * 100
    
    # Get most consumed medication
    med_consumption = {}
    for record in consumption_records:
        med_name = record.medication.name
        med_consumption[med_name] = med_consumption.get(med_name, 0) + record.quantity
    
    most_consumed_med = max(med_consumption.items(), key=lambda x: x[1])[0] if med_consumption else 'N/A'
    
    # Prepare data for trend chart
    dates = []
    daily_doses = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        day_doses = sum(
            record.quantity
            for record in consumption_records
            if record.taken_at.date() == current_date.date()
        )
        daily_doses.append(day_doses)
        current_date += timedelta(days=1)
    
    # Calculate status distribution
    status_counts = {'taken': 0, 'missed': 0, 'skipped': 0}
    for record in consumption_records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    status_distribution = [
        status_counts.get('taken', 0),
        status_counts.get('missed', 0),
        status_counts.get('skipped', 0)
    ]
    
    # Get all medications for the filter dropdown
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'reports.html',
        medications=medications,
        consumption_records=consumption_records,
        total_consumption=total_consumption,
        adherence_rate=adherence_rate,
        most_consumed_med=most_consumed_med,
        dates=dates,
        daily_doses=daily_doses,
        status_distribution=status_distribution,
        date_range=date_range,
        medication_id=medication_id
    )