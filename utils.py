import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from app import db
from models import ActivityLog
from flask import session

def load_chemical_database():
    """Load chemical database from JSON file."""
    chemicals_file = os.path.join('data', 'chemicals.json')
    try:
        with open(chemicals_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_chemical_data(chemical_name):
    """Get chemical data by name or formula."""
    chemicals = load_chemical_database()
    
    # Search by name (case insensitive)
    for chemical in chemicals.values():
        if chemical['name'].lower() == chemical_name.lower():
            return chemical
        # Also search by formula
        if chemical.get('formula', '').lower() == chemical_name.lower():
            return chemical
        # Search by common names
        for common_name in chemical.get('common_names', []):
            if common_name.lower() == chemical_name.lower():
                return chemical
    
    return None

def calculate_reagent_mass(molarity, volume_liters, molecular_weight):
    """Calculate mass of reagent required for a given molarity and volume."""
    # Mass (g) = Molarity (mol/L) × Volume (L) × Molecular Weight (g/mol)
    return molarity * volume_liters * molecular_weight

def generate_pdf_report(title, content, report_type):
    """Generate a PDF report using ReportLab."""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12
    )
    
    # Build document content
    story = []
    
    # Title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))
    
    # Report metadata
    story.append(Paragraph(f"Report Type: {report_type.title()}", header_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Content
    story.append(Paragraph("Report Content", header_style))
    
    # Split content into paragraphs
    paragraphs = content.split('\n')
    for paragraph in paragraphs:
        if paragraph.strip():
            story.append(Paragraph(paragraph, styles['Normal']))
            story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content

def log_activity(action_type, description, details=None):
    """Log user activity to the database."""
    try:
        activity = ActivityLog(
            action_type=action_type,
            description=description,
            details=details,
            session_id=session.get('session_id', 'unknown')
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
