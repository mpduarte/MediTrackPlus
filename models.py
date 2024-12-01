from datetime import datetime
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    medications = db.relationship('Medication', backref='user', lazy=True)

class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    current_stock = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_time = db.Column(db.String(50))  # Store time in HH:MM format
    max_daily_doses = db.Column(db.Integer, default=1)
    consumptions = db.relationship('Consumption', backref='medication', lazy=True, cascade='all, delete-orphan')
    inventory_logs = db.relationship('InventoryLog', backref='medication', lazy=True, cascade='all, delete-orphan')
    
    def get_doses_taken_today(self):
        today = datetime.utcnow().date()
        return Consumption.query.filter(
            Consumption.medication_id == self.id,
            db.func.date(Consumption.taken_at) == today
        ).count()
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'current_stock': self.current_stock,
            'scheduled_time': self.scheduled_time,
            'max_daily_doses': self.max_daily_doses
        }

class Consumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Integer, nullable=False)
    scheduled_time = db.Column(db.String(50))  # Store scheduled time when dose was taken
    status = db.Column(db.String(20), default='taken')  # taken, missed, skipped

class InventoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)  # 'add' or 'remove'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    medication = db.relationship('Medication', backref='prescriptions')
