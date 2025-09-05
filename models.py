from app import db
from datetime import datetime
from sqlalchemy import Text

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(Text, nullable=False)
    details = db.Column(Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<ActivityLog {self.action_type}: {self.description}>'

class Calculation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chemical_name = db.Column(db.String(100), nullable=False)
    molarity = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)
    mass_required = db.Column(db.Float, nullable=False)
    molecular_weight = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<Calculation {self.chemical_name}: {self.mass_required}g>'

class LabReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(Text, nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<LabReport {self.title}>'
