import json
import os
from flask import render_template, request, jsonify, session, redirect, url_for, make_response, flash
from datetime import datetime, timedelta
from app import app, db
from models import ActivityLog, Calculation, LabReport
from utils import generate_pdf_report, calculate_reagent_mass, get_chemical_data, log_activity
import uuid

@app.before_request
def before_request():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Check if user is logged in for protected routes
    protected_routes = ['dashboard', 'calculator', 'msds', 'safety', 'documentation', 'activity_logs', 'profile']
    if request.endpoint in protected_routes and 'user_name' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form.get('user_name', '').strip()
        lab_role = request.form.get('lab_role', '').strip()
        institution = request.form.get('institution', '').strip()
        
        if not user_name or not lab_role:
            flash('Please provide your name and select your laboratory role.', 'error')
            return render_template('login.html')
        
        # Store user information in session
        session['user_name'] = user_name
        session['lab_role'] = lab_role
        session['institution'] = institution
        session['login_time'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Log the login activity
        log_activity('authentication', f'User {user_name} ({lab_role}) logged in')
        
        flash(f'Welcome to LabMate AI, {user_name}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_name' in session:
        user_name = session['user_name']
        log_activity('authentication', f'User {user_name} logged out')
    
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        session['user_name'] = request.form.get('user_name', '').strip()
        session['lab_role'] = request.form.get('lab_role', '').strip()
        session['institution'] = request.form.get('institution', '').strip()
        
        log_activity('profile', 'Updated profile information')
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    # Calculate session statistics
    total_calculations = Calculation.query.filter_by(session_id=session['session_id']).count()
    total_activities = ActivityLog.query.filter_by(session_id=session['session_id']).count()
    
    # Calculate session duration
    session_duration = "Not available"
    if 'login_time' in session:
        try:
            login_time = datetime.strptime(session['login_time'], '%Y-%m-%d %H:%M:%S UTC')
            duration = datetime.utcnow() - login_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            session_duration = f"{int(hours)}h {int(minutes)}m"
        except:
            pass
    
    return render_template('profile.html',
                         total_calculations=total_calculations,
                         total_activities=total_activities,
                         session_duration=session_duration)

@app.route('/')
def dashboard():
    # Get recent activity
    recent_activity = ActivityLog.query.filter_by(session_id=session['session_id']).order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    # Get today's statistics
    today = datetime.utcnow().date()
    calculations_today = Calculation.query.filter(
        Calculation.session_id == session['session_id'],
        Calculation.timestamp >= today
    ).count()
    
    total_activities = ActivityLog.query.filter_by(session_id=session['session_id']).count()
    
    return render_template('dashboard.html', 
                         recent_activity=recent_activity,
                         calculations_today=calculations_today,
                         total_activities=total_activities)

@app.route('/api/recent_activity')
def api_recent_activity():
    recent_activity = ActivityLog.query.filter_by(session_id=session['session_id']).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    activities = []
    for activity in recent_activity:
        activities.append({
            'description': activity.description,
            'action_type': activity.action_type,
            'timestamp': activity.timestamp.strftime('%H:%M')
        })
    return jsonify(activities)

@app.route('/api/stats')
def api_stats():
    today = datetime.utcnow().date()
    calculations_today = Calculation.query.filter(
        Calculation.session_id == session['session_id'],
        Calculation.timestamp >= today
    ).count()
    
    total_activities = ActivityLog.query.filter_by(session_id=session['session_id']).count()
    
    return jsonify({
        'calculations_today': calculations_today,
        'total_activities': total_activities
    })

@app.route('/voice_command', methods=['POST'])
def voice_command():
    try:
        data = request.get_json()
        command = data.get('command', '').strip().lower()
        original = data.get('original', command)
        
        if not command:
            return jsonify({'success': False, 'error': 'No command provided'})
        
        # Log the voice command
        log_activity('voice_command', f'Voice command: "{original}"')
        
        # Parse the command for laboratory operations
        result = parse_lab_command(command)
        
        if result['action'] == 'calculation':
            # Process calculation command
            calc_result = process_calculation_command(result)
            if calc_result['success']:
                return jsonify({
                    'success': True,
                    'action': 'calculation',
                    'response': calc_result['response'],
                    'result': calc_result['data']
                })
            else:
                return jsonify({'success': False, 'error': calc_result['error']})
        
        elif result['action'] == 'navigation':
            return jsonify({
                'success': True,
                'action': 'navigation',
                'response': f"Navigating to {result['target']}",
                'result': {'url': result['url']}
            })
        
        elif result['action'] == 'help':
            return jsonify({
                'success': True,
                'action': 'help',
                'response': get_voice_help_message(),
                'result': {}
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Sorry, I did not understand that command. Try saying "calculate", "navigate to", or "help"'
            })
            
    except Exception as e:
        import traceback
        app.logger.error(f"Voice command error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Sorry, there was an error processing your command'})

def parse_lab_command(command):
    """Parse laboratory voice commands into structured data"""
    import re
    
    # Calculation patterns - enhanced for better voice recognition
    calc_patterns = [
        r'calculate\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*(\w+)\s+for\s+(\d+)\s*(ml|l|liter|milliliters?)',
        r'calculate\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*of\s+(\w+)\s+for\s+(\d+)\s*(ml|l|liter|milliliters?)',
        r'calculate\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*(\w+)',
        r'prepare\s+(\d+)\s*(ml|l|liter|milliliters?)\s+of\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*(\w+)',
        r'make\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*(\w+)\s+solution\s+(\d+)\s*(ml|l|liter|milliliters?)',
        r'make\s+(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*of\s+(\w+)',
        r'(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*(\w+)\s+in\s+(\d+)\s*(ml|l|liter|milliliters?)',
        r'(\d*\.?\d+)\s*(m|molar|molarity|molecular)?\s*of\s+(\w+)'
    ]
    
    for pattern in calc_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # Default values
            molarity = 1.0
            chemical = None
            volume = 250.0  # Default to 250ml
            
            # Enhanced parsing logic
            try:
                # Find numbers in the groups
                numbers = [float(g) for g in groups if g and g.replace('.', '').isdigit()]
                # Find chemical names (non-numeric, non-unit groups)
                chemicals = [g for g in groups if g and not g.replace('.', '').isdigit() 
                           and g.lower() not in ['m', 'molar', 'molarity', 'molecular', 'ml', 'l', 'liter', 'milliliters', 'milliliter']]
                
                if numbers:
                    molarity = numbers[0]
                    if len(numbers) > 1:
                        volume = numbers[1]
                
                if chemicals:
                    chemical = chemicals[0].strip()
                
                # Fallback: try to extract from the original command
                if not chemical:
                    # Look for common chemical patterns
                    chem_match = re.search(r'(nacl|kcl|cacl2|h2so4|hcl|naoh|mgso4)', command, re.IGNORECASE)
                    if chem_match:
                        chemical = chem_match.group(1)
                
            except (ValueError, IndexError):
                # Fallback parsing
                if len(groups) >= 3:
                    try:
                        molarity = float(groups[0]) if groups[0] and groups[0].replace('.', '').isdigit() else 1.0
                        chemical = groups[2] if groups[2] else 'NaCl'
                        volume = float(groups[3]) if len(groups) > 3 and groups[3] and groups[3].replace('.', '').isdigit() else 250.0
                    except:
                        molarity, chemical, volume = 1.0, 'NaCl', 250.0
            
            return {
                'action': 'calculation',
                'chemical': chemical or 'NaCl',
                'molarity': molarity,
                'volume': volume
            }
    
    # Navigation patterns
    nav_patterns = {
        r'(go to|navigate to|open)\s+(calculator|calc)': '/calculator',
        r'(go to|navigate to|open)\s+(safety|protocols)': '/safety',
        r'(go to|navigate to|open)\s+(msds|safety data)': '/msds',
        r'(go to|navigate to|open)\s+(documentation|docs|reports)': '/documentation',
        r'(go to|navigate to|open)\s+(dashboard|home)': '/',
        r'(go to|navigate to|open)\s+(activity|logs)': '/activity_logs'
    }
    
    for pattern, url in nav_patterns.items():
        if re.search(pattern, command, re.IGNORECASE):
            return {
                'action': 'navigation',
                'target': url.split('/')[-1] or 'dashboard',
                'url': url
            }
    
    # Help patterns
    if re.search(r'help|what can you do|commands', command, re.IGNORECASE):
        return {'action': 'help'}
    
    return {'action': 'unknown', 'command': command}

def process_calculation_command(parsed_result):
    """Process a parsed calculation command"""
    try:
        chemical_name = parsed_result['chemical']
        molarity = parsed_result['molarity']
        volume = parsed_result['volume']
        
        # Get chemical data
        chemical_data = get_chemical_data(chemical_name)
        if not chemical_data:
            return {
                'success': False,
                'error': f'Chemical data not found for {chemical_name}. Please try the full chemical name or formula.'
            }
        
        # Calculate mass required
        mass_required = calculate_reagent_mass(molarity, volume, chemical_data['molecular_weight'])
        
        # Save calculation
        calculation = Calculation(
            chemical_name=chemical_name,
            molarity=molarity,
            volume=volume,
            mass_required=mass_required,
            molecular_weight=chemical_data['molecular_weight'],
            session_id=session['session_id']
        )
        db.session.add(calculation)
        db.session.commit()
        
        # Log activity
        log_activity('voice_calculation', f'Voice calculated {mass_required:.4f}g of {chemical_name}')
        
        response = f"To prepare {volume}ml of {molarity}M {chemical_name}, you need {mass_required:.3f} grams"
        
        return {
            'success': True,
            'response': response,
            'data': {
                'chemical_name': chemical_name,
                'molarity': molarity,
                'volume': volume,
                'mass_required': mass_required,
                'molecular_weight': chemical_data['molecular_weight']
            }
        }
        
    except Exception as e:
        app.logger.error(f"Calculation error: {str(e)}")
        return {
            'success': False,
            'error': f'Error calculating: {str(e)}'
        }

def get_voice_help_message():
    """Get help message for voice commands"""
    return """I can help you with laboratory calculations and navigation. Try saying:
    - "Calculate 0.1 molar sodium chloride for 250 ml"
    - "Prepare 500 ml of 0.5 M NaCl"
    - "Go to calculator"
    - "Navigate to safety protocols"
    - "Open MSDS lookup"
    """

@app.route('/calculator')
def calculator():
    log_activity('navigation', 'Accessed reagent calculator')
    return render_template('calculator.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json() if request.is_json else request.form
        
        chemical_name = data.get('chemical_name', '').strip()
        molarity = float(data.get('molarity', 0))
        volume = float(data.get('volume', 0))
        
        if not chemical_name or molarity <= 0 or volume <= 0:
            return jsonify({'error': 'Please provide valid chemical name, molarity, and volume'}), 400
        
        # Get chemical data
        chemical_data = get_chemical_data(chemical_name)
        if not chemical_data:
            return jsonify({'error': f'Chemical data not found for {chemical_name}'}), 404
        
        # Calculate mass required
        mass_required = calculate_reagent_mass(molarity, volume, chemical_data['molecular_weight'])
        
        # Save calculation
        calculation = Calculation(
            chemical_name=chemical_name,
            molarity=molarity,
            volume=volume,
            mass_required=mass_required,
            molecular_weight=chemical_data['molecular_weight'],
            session_id=session['session_id']
        )
        db.session.add(calculation)
        db.session.commit()
        
        # Log activity
        log_activity('calculation', f'Calculated {mass_required:.4f}g of {chemical_name}')
        
        result = {
            'chemical_name': chemical_name,
            'molarity': molarity,
            'volume': volume,
            'mass_required': round(mass_required, 4),
            'molecular_weight': chemical_data['molecular_weight'],
            'formula': chemical_data.get('formula', 'N/A'),
            'hazards': chemical_data.get('hazards', [])
        }
        
        if request.is_json:
            return jsonify(result)
        else:
            return render_template('calculator.html', result=result)
            
    except ValueError as e:
        error_msg = 'Invalid numeric values provided'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        return render_template('calculator.html', error=error_msg)
    except Exception as e:
        app.logger.error(f"Calculation error: {str(e)}")
        error_msg = 'An error occurred during calculation'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        return render_template('calculator.html', error=error_msg)

@app.route('/msds')
def msds():
    log_activity('navigation', 'Accessed MSDS lookup')
    return render_template('msds.html')

@app.route('/msds_search', methods=['POST'])
def msds_search():
    try:
        data = request.get_json() if request.is_json else request.form
        chemical_name = data.get('chemical_name', '').strip()
        
        if not chemical_name:
            return jsonify({'error': 'Please provide a chemical name'}), 400
        
        chemical_data = get_chemical_data(chemical_name)
        if not chemical_data:
            return jsonify({'error': f'MSDS data not found for {chemical_name}'}), 404
        
        # Log activity
        log_activity('msds_lookup', f'Looked up MSDS for {chemical_name}')
        
        if request.is_json:
            return jsonify(chemical_data)
        else:
            return render_template('msds.html', chemical_data=chemical_data)
            
    except Exception as e:
        app.logger.error(f"MSDS search error: {str(e)}")
        error_msg = 'An error occurred during MSDS lookup'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        return render_template('msds.html', error=error_msg)

@app.route('/safety')
def safety():
    log_activity('navigation', 'Accessed safety protocols')
    
    # Load safety protocols
    protocols_file = os.path.join('data', 'safety_protocols.json')
    protocols = []
    try:
        with open(protocols_file, 'r') as f:
            protocols = json.load(f)
    except FileNotFoundError:
        app.logger.error(f"Safety protocols file not found: {protocols_file}")
    
    return render_template('safety.html', protocols=protocols)

@app.route('/documentation')
def documentation():
    log_activity('navigation', 'Accessed documentation')
    
    # Get recent reports
    recent_reports = LabReport.query.filter_by(session_id=session['session_id']).order_by(LabReport.created_at.desc()).limit(10).all()
    
    return render_template('documentation.html', recent_reports=recent_reports)

@app.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json() if request.is_json else request.form
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        report_type = data.get('report_type', 'general').strip()
        
        if not title or not content:
            return jsonify({'error': 'Please provide both title and content'}), 400
        
        # Save report to database
        report = LabReport(
            title=title,
            content=content,
            report_type=report_type,
            session_id=session['session_id']
        )
        db.session.add(report)
        db.session.commit()
        
        # Generate PDF
        pdf_content = generate_pdf_report(title, content, report_type)
        
        # Log activity
        log_activity('documentation', f'Generated report: {title}')
        
        if request.is_json:
            return jsonify({'message': 'Report generated successfully', 'report_id': report.id})
        
        # Return PDF as download
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{title}.pdf"'
        return response
        
    except Exception as e:
        app.logger.error(f"Report generation error: {str(e)}")
        error_msg = 'An error occurred during report generation'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        return render_template('documentation.html', error=error_msg)

@app.route('/activity_logs')
def activity_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    activities = ActivityLog.query.filter_by(session_id=session['session_id']).order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('activity_logs.html', activities=activities)


