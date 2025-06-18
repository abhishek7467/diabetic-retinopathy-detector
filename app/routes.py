import os
import json
import csv
import sys
import flask
import traceback
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app, send_file, Response, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from markupsafe import Markup
from io import StringIO, BytesIO
from ultralytics import YOLO
from app.models import User, ImageRecord, db
from app.utils import allowed_file, save_image, format_prediction_result, send_otp_email, send_otp_sms, send_otp, validate_phone_number
from app.utils import generate_pdf_report, create_analytics_chart, send_report_via_email
from models.yolov8_classifier import predict


main = Blueprint('main', __name__)

# Initialize classifier (will be created when first needed)
classifier = None

@main.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return make_response('', 204)  # Return empty response with No Content status

def get_upload_folder():
    """Get the correct path to the uploads folder"""
    # The uploads folder is in the project root, not in the app directory
    project_root = os.path.dirname(current_app.root_path)
    upload_folder = os.path.join(project_root, current_app.config['UPLOAD_FOLDER'])
    return upload_folder

# Home/Dashboard route
@main.route('/')
def index():
    if current_user.is_authenticated:
        # Get user's recent uploads - increased limit to show more images for pagination
        recent_images = ImageRecord.query.filter_by(user_id=current_user.id)\
                                        .order_by(ImageRecord.created_at.desc())\
                                        .limit(20).all()
        
        print(f"DEBUG: Found {len(recent_images)} recent images for user {current_user.id}")
        print(f"DEBUG: Image filenames: {[img.filename for img in recent_images]}")
        
        # Calculate statistics
        all_user_images = ImageRecord.query.filter_by(user_id=current_user.id).all()
        total_images = len(all_user_images)
        
        # Debug: Print prediction classes to see what we have
        print(f"DEBUG: Total images for user {current_user.id}: {total_images}")
        for img in all_user_images:
            print(f"DEBUG: Image {img.filename} - Prediction: '{img.prediction_class}' (type: {type(img.prediction_class)})")
        
        # Updated: Count based on new class names: {0: 'Mild', 1: 'Moderate', 2: 'No_DR', 3: 'Proliferate_DR', 4: 'Severe'}
        no_dr_count = sum(1 for img in all_user_images if img.prediction_class == 'No_DR')
        mild_dr_count = sum(1 for img in all_user_images if img.prediction_class == 'Mild')
        moderate_dr_count = sum(1 for img in all_user_images if img.prediction_class == 'Moderate')
        severe_dr_count = sum(1 for img in all_user_images if img.prediction_class == 'Severe')
        proliferate_dr_count = sum(1 for img in all_user_images if img.prediction_class == 'Proliferate_DR')
        
        print(f"DEBUG: no_dr_count: {no_dr_count}, mild_dr_count: {mild_dr_count}, moderate_dr_count: {moderate_dr_count}, severe_dr_count: {severe_dr_count}, proliferate_dr_count: {proliferate_dr_count}")
        
        return render_template('dashboard.html', 
                             recent_images=recent_images,
                             current_time=datetime.now(),
                             total_images=total_images,
                             no_dr_count=no_dr_count,
                             mild_dr_count=mild_dr_count,
                             moderate_dr_count=moderate_dr_count,
                             severe_dr_count=severe_dr_count,
                             proliferate_dr_count=proliferate_dr_count)
    return render_template('index.html')

# Authentication routes
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return render_template('register.html')
            
        # Validate phone number if provided
        if phone_number:
            is_valid, formatted_number = validate_phone_number(phone_number)
            if not is_valid:
                flash('Invalid phone number format. Please include country code (e.g. +1 for USA).', 'danger')
                return render_template('register.html')
            phone_number = formatted_number
        
        # Create new user
        user = User(
            name=name, 
            email=email,
            phone_number=phone_number if phone_number else None
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
    
@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Update name
        if name and name != current_user.name:
            current_user.name = name
        
        # Update phone number
        if phone_number != current_user.phone_number:
            # Validate phone number if provided
            if phone_number:
                is_valid, formatted_number = validate_phone_number(phone_number)
                if not is_valid:
                    flash('Invalid phone number format. Please include country code (e.g. +1 for USA).', 'danger')
                    return render_template('profile.html')
                phone_number = formatted_number
                
            current_user.phone_number = phone_number if phone_number else None
            
        # Update password if provided
        if current_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
                return render_template('profile.html')
                
            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return render_template('profile.html')
                
            if new_password:
                current_user.set_password(new_password)
                flash('Password updated successfully', 'success')
        
        # Save changes
        db.session.commit()
        flash('Profile updated successfully', 'success')
        
    return render_template('profile.html')

@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        otp_method = request.form.get('otp_method', 'email')
        user = None
        identifier = None
        
        if otp_method == 'email':
            email = request.form.get('email')
            identifier = email
            if email:
                user = User.query.filter_by(email=email).first()
        else:  # phone method
            phone = request.form.get('phone')
            
            # Basic validation of phone number
            if phone:
                is_valid, formatted_number = validate_phone_number(phone)
                if is_valid:
                    phone = formatted_number
                    
            identifier = phone
            if phone:
                user = User.query.filter_by(phone_number=phone).first()
        
        if user:
            success = False
            message = 'email' if otp_method == 'email' else 'phone'
            
            if otp_method == 'email':
                # For email, generate our own OTP
                otp = user.generate_otp(method=otp_method)
                db.session.commit()
                success = send_otp_email(user, otp)
            else:
                # For phone, handle both Twilio Verify and other SMS services
                if current_app.config.get('SMS_SERVICE') == 'twilio' and current_app.config.get('USE_TWILIO_VERIFY'):
                    # Using Twilio Verify - send_otp_sms will store verification SID as OTP
                    user.otp_method = otp_method
                    user.otp_created_at = datetime.utcnow()
                    db.session.commit()
                    success = send_otp_sms(user, None)  # No OTP needed for Twilio Verify
                else:
                    # Using other SMS service - generate our own OTP
                    otp = user.generate_otp(method=otp_method)
                    db.session.commit()
                    success = send_otp_sms(user, otp)
            
            if success:
                flash(f'An OTP has been sent to your {message}. Please check and enter the code.', 'success')
                # Pass identifier and method for later use
                return redirect(url_for('main.verify_otp', identifier=identifier, method=otp_method))
            else:
                flash(f'Failed to send OTP to your {message}. Please try again later.', 'danger')
        else:
            # For security reasons, don't disclose if user exists or not
            flash('If your details exist in our system, you will receive an OTP shortly.', 'info')
            
    return render_template('forgot_password.html')
    
@main.route('/verify-otp/<identifier>/<method>', methods=['GET', 'POST'])
def verify_otp(identifier, method):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Find user based on the method used
    user = None
    if method == 'email':
        user = User.query.filter_by(email=identifier).first()
        contact_info = identifier
    else:  # method == 'phone'
        user = User.query.filter_by(phone_number=identifier).first()
        # Mask the phone number for display
        if identifier and len(identifier) > 4:
            contact_info = '****' + identifier[-4:]
        else:
            contact_info = identifier
    
    if not user:
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if user.verify_otp(otp):
            # Generate reset token for password reset
            token = user.generate_reset_token()
            db.session.commit()
            return redirect(url_for('main.reset_password', token=token))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
        
    return render_template('verify_otp.html', contact_info=contact_info, method=method)
    
@main.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token. Please try again.', 'danger')
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html')
            
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated! Please log in.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html')

# Image upload and prediction routes
@main.route('/upload')
@login_required
def upload_page():
    return render_template('upload.html')

# Route to serve uploaded images
@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images"""
    try:
        # Get the correct upload folder path
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, filename)
        
        print(f"App root path: {current_app.root_path}")
        print(f"Upload folder: {upload_folder}")
        print(f"Looking for file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            flash('Image not found!', 'error')
            return redirect(url_for('main.index'))
        
        return send_file(file_path)
    except Exception as e:
        print(f"Error serving file {filename}: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading image!', 'error')
        return redirect(url_for('main.index'))


@main.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('main.upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('main.upload_page'))
    
    if file and allowed_file(file.filename):
        try:
            # Save image
            upload_folder = get_upload_folder()
            filename = save_image(file, upload_folder)
            image_path = os.path.join(upload_folder, filename)
            
            # Get prediction
            yolo_model = YOLO(current_app.config['YOLOV8_MODEL_PATH'])
            prediction = predict(yolo_model, image_path)
            print(f"✅ Prediction result for the model: {prediction}")
            
            # Handle confidence threshold logic
            if not prediction['threshold_met']:
                # For low confidence predictions, store as "No reliable detection"
                # but still save the actual confidence and details for record keeping
                image_record = ImageRecord(
                    filename=filename,
                    original_filename=file.filename,
                    user_id=current_user.id,
                    prediction_class='No reliable detection',
                    confidence=prediction['actual_confidence'],  # Store actual confidence
                    prediction_details=json.dumps({
                        'threshold_info': {
                            'threshold_met': False,
                            'threshold_value': prediction['threshold_value'],
                            'actual_confidence': prediction['actual_confidence'],
                            'message': prediction['message']
                        },
                        'predicted_class_only': prediction['predicted_class_only']
                    })
                )
                # Add flash message for low confidence
                flash(f"Analysis complete, but confidence is below 60% threshold. {prediction['message']}", 'warning')
            else:
                # For high confidence predictions, store normally
                image_record = ImageRecord(
                    filename=filename,
                    original_filename=file.filename,
                    user_id=current_user.id,
                    prediction_class=prediction['class_name'],
                    confidence=prediction['confidence'],
                    prediction_details=json.dumps({
                        'threshold_info': {
                            'threshold_met': True,
                            'threshold_value': prediction['threshold_value'],
                            'actual_confidence': prediction['actual_confidence'],
                            'message': prediction['message']
                        },
                        'predicted_class_only': prediction['predicted_class_only']
                    })
                )
                flash(f"Analysis complete! {prediction['message']}", 'success')
            
            db.session.add(image_record)
            db.session.commit()
            
            return render_template('result.html', 
                                 prediction=prediction, 
                                 filename=filename,
                                 image_record=image_record)
            
        except Exception as e:
            flash(f'Error processing image: {str(e)}', 'danger')
            return redirect(url_for('main.upload_page'))
    else:
        flash('Invalid file type! Please upload PNG, JPG, or JPEG files.', 'danger')
        return redirect(url_for('main.upload_page'))

# History routes
@main.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('RECORDS_PER_PAGE', 10)
    
    # Get paginated records
    pagination = ImageRecord.query.filter_by(user_id=current_user.id)\
                                  .order_by(ImageRecord.created_at.desc())\
                                  .paginate(
                                      page=page, 
                                      per_page=per_page,
                                      error_out=False
                                  )
    
    records = pagination.items
    
    # Calculate statistics
    all_records = ImageRecord.query.filter_by(user_id=current_user.id).all()
    normal_count = sum(1 for r in all_records if r.prediction_class == 'No_DR')
    dr_count = len(all_records) - normal_count
    avg_confidence = sum(r.confidence or 0 for r in all_records) / len(all_records) if all_records else 0
    
    return render_template('history.html', 
                         records=records,
                         pagination=pagination,
                         normal_count=normal_count,
                         dr_count=dr_count,
                         avg_confidence=avg_confidence * 100)

@main.route('/delete_image/<int:image_id>')
@login_required
def delete_image(image_id):
    image = ImageRecord.query.get_or_404(image_id)
    
    # Check if user owns this image
    if image.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.history'))
    
    # Delete file from disk
    try:
        file_path = os.path.join(get_upload_folder(), image.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    # Delete from database
    db.session.delete(image)
    db.session.commit()
    
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('main.history'))

# Admin routes
@main.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all users and recent analyses
    users = User.query.all()
    recent_analyses = ImageRecord.query.order_by(ImageRecord.created_at.desc()).limit(10).all()
    
    # Calculate statistics
    total_users = len(users)
    total_analyses = ImageRecord.query.count()
    dr_cases = ImageRecord.query.filter(ImageRecord.prediction_class != 'No_DR').count()
    normal_cases = total_analyses - dr_cases
    
    # Active users in last 24 hours (simplified calculation since User model doesn't have last_login)
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    # Count users who have made analyses in the last 24 hours as a proxy for active users
    active_users = db.session.query(User.id).join(ImageRecord).filter(ImageRecord.created_at >= yesterday).distinct().count()
    
    stats = {
        'total_users': total_users,
        'total_analyses': total_analyses,
        'dr_cases': dr_cases,
        'normal_cases': normal_cases,
        'active_users': active_users
    }
    
    # System information
    import sys
    import flask
    system_info = {
        'python_version': sys.version.split()[0],
        'flask_version': getattr(flask, '__version__', '2.0.0'),
        'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI', 'SQLite').split('://')[0],
        'upload_folder': current_app.config.get('UPLOAD_FOLDER', 'uploads'),
        'storage_used': '0 MB',  # You can implement actual storage calculation
        'storage_percentage': 0
    }
    
    # Usage data for charts (last 7 days)
    usage_labels = []
    usage_data = []
    for i in range(6, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        usage_labels.append(date.strftime('%m/%d'))
        daily_count = ImageRecord.query.filter(
            ImageRecord.created_at >= date.replace(hour=0, minute=0, second=0),
            ImageRecord.created_at < date.replace(hour=23, minute=59, second=59)
        ).count()
        usage_data.append(daily_count)
    
    return render_template('admin.html', 
                         users=users, 
                         recent_analyses=recent_analyses,
                         stats=stats,
                         system_info=system_info,
                         usage_labels=json.dumps(usage_labels),
                         usage_data=json.dumps(usage_data))

@main.route('/admin/export_csv')
@login_required
def export_csv():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.index'))
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['ID', 'User Name', 'User Email', 'Original Filename', 
                    'Prediction', 'Confidence', 'Upload Date'])
    
    # Write data
    images = ImageRecord.query.join(User).all()
    for image in images:
        writer.writerow([
            image.id,
            image.user.name,
            image.user.email,
            image.original_filename,
            image.prediction_class,
            f"{image.confidence:.2%}" if image.confidence else 'N/A',
            image.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Create file-like object
    output.seek(0)
    
    # Create BytesIO from string
    mem = BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        as_attachment=True,
        download_name=f'retinopatia_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        mimetype='text/csv'
    )

@main.route('/about')
def about():
    return render_template('about_us.html')

@main.route('/how-to-use')
def how_to_use():
    return render_template('how_to_use.html')

# Enhanced Report Features
@main.route('/result/<int:record_id>')
@login_required
def result(record_id):
    """Display detailed result page for a specific record"""
    record = ImageRecord.query.get_or_404(record_id)
    
    # Check if user owns this record or is admin
    if record.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.history'))
    
    # Reconstruct prediction object from database record
    prediction = {
        'class_name': record.prediction_class,
        'confidence': record.confidence,
        'all_probabilities': json.loads(record.prediction_details) if record.prediction_details else {}
    }
    
    return render_template('result.html', 
                         image_record=record, 
                         prediction=prediction, 
                         filename=record.filename)

@main.route('/download-report/<int:record_id>')
@login_required
def download_report(record_id):
    """Generate and download PDF report for a specific analysis"""
    record = ImageRecord.query.get_or_404(record_id)
    
    # Check if user owns this record or is admin
    if record.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.history'))
    
    try:
        # Generate PDF report
        app_url = request.url_root.rstrip('/')
        pdf_filename = generate_pdf_report(record.user, record, app_url)
        
        if pdf_filename:
            # Use absolute path to uploads folder
            upload_folder = get_upload_folder()
            pdf_path = os.path.join(upload_folder, pdf_filename)
            
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"DR_Report_{record.user.name.replace(' ', '_')}_{record.created_at.strftime('%Y%m%d')}.pdf",
                mimetype='application/pdf'
            )
        else:
            flash('Error generating PDF report. Please try again.', 'danger')
            return redirect(url_for('main.result', record_id=record_id))
            
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('main.result', record_id=record_id))

@main.route('/share-report/<int:record_id>', methods=['GET', 'POST'])
@login_required
def share_report(record_id):
    """Share PDF report via email"""
    record = ImageRecord.query.get_or_404(record_id)
    
    # Check if user owns this record or is admin
    if record.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.history'))
    
    if request.method == 'POST':
        recipient_email = request.form.get('email', '').strip()
        personal_message = request.form.get('message', '').strip()
        consent = request.form.get('consent')
        public_share = request.form.get('public_share')  # New option for public sharing
        
        if not recipient_email:
            flash('Please provide a valid email address.', 'danger')
            return render_template('share_report.html', record=record)
        
        try:
            # Generate PDF report
            app_url = request.url_root.rstrip('/')
            pdf_filename = generate_pdf_report(record.user, record, app_url)
            
            if pdf_filename:
                # Use absolute path to uploads folder
                upload_folder = get_upload_folder()
                pdf_path = os.path.join(upload_folder, pdf_filename)
                
                # Send via email
                success = send_report_via_email(record.user.email, pdf_path, recipient_email)
                
                if success:
                    flash_message = f'Report successfully sent to {recipient_email}!'
                    
                    # If public sharing is requested and consent is given
                    if public_share and consent:
                        try:
                            from app.utils import auto_share_report_publicly
                            public_url = auto_share_report_publicly(record.user, record, consent=True)
                            if public_url:
                                flash_message += f' Public link created: <a href="{public_url}" target="_blank">{public_url}</a>'
                                flash(Markup(flash_message), 'success')
                            else:
                                flash(flash_message + ' Note: Public sharing temporarily unavailable.', 'warning')
                        except Exception as e:
                            print(f"Public sharing error: {e}")
                            flash(flash_message + ' Note: Public sharing failed but email was sent successfully.', 'warning')
                    else:
                        flash(flash_message, 'success')
                    
                    return redirect(url_for('main.result', record_id=record_id))
                else:
                    flash('Failed to send report via email. Please try again later.', 'danger')
            else:
                flash('Error generating PDF report. Please try again.', 'danger')
                
        except Exception as e:
            flash(f'Error sharing report: {str(e)}', 'danger')
    
    return render_template('share_report.html', record=record)

@main.route('/my-analytics')
@login_required
def my_analytics():
    """Display user's personal analytics dashboard"""
    try:
        # Get user's records
        records = ImageRecord.query.filter_by(user_id=current_user.id).order_by(ImageRecord.created_at).all()
        
        if len(records) < 2:
            flash('You need at least 2 analyses to view analytics.', 'info')
            return redirect(url_for('main.history'))
        
        # Generate analytics chart
        chart_buffer = create_analytics_chart(current_user.id)
        
        # Calculate statistics
        total_tests = len(records)
        normal_cases = sum(1 for r in records if r.prediction_class == 'No_DR')
        dr_cases = total_tests - normal_cases
        avg_confidence = sum(r.confidence or 0 for r in records) / total_tests if total_tests > 0 else 0
        
        # Recent trend (last 5 tests)
        recent_records = records[-5:] if len(records) >= 5 else records
        recent_dr_cases = sum(1 for r in recent_records if r.prediction_class != 'No_DR')
        trend = "improving" if recent_dr_cases < (dr_cases / total_tests * len(recent_records)) else "stable"
        
        stats = {
            'total_tests': total_tests,
            'normal_cases': normal_cases,
            'dr_cases': dr_cases,
            'avg_confidence': avg_confidence * 100,
            'trend': trend,
            'first_test_date': records[0].created_at,
            'last_test_date': records[-1].created_at
        }
        
        return render_template('analytics.html', stats=stats, has_chart=chart_buffer is not None)
        
    except Exception as e:
        flash(f'Error generating analytics: {str(e)}', 'danger')
        return redirect(url_for('main.history'))

@main.route('/analytics-chart')
@login_required
def analytics_chart():
    """Serve analytics chart image"""
    try:
        chart_buffer = create_analytics_chart(current_user.id)
        
        if chart_buffer:
            return Response(chart_buffer.getvalue(), mimetype='image/png')
        else:
            # Return a placeholder image or redirect
            return redirect(url_for('static', filename='images/no-chart.png'))
            
    except Exception as e:
        print(f"Error serving analytics chart: {e}")
        return redirect(url_for('static', filename='images/no-chart.png'))

@main.route('/compare-results')
@login_required
def compare_results():
    """Compare multiple test results"""
    # Get selected record IDs from query parameters
    record_ids = request.args.getlist('records', type=int)
    
    if len(record_ids) < 2:
        flash('Please select at least 2 records to compare.', 'warning')
        return redirect(url_for('main.history'))
    
    if len(record_ids) > 5:
        flash('You can compare up to 5 records at a time.', 'warning')
        record_ids = record_ids[:5]
    
    # Get records
    records = ImageRecord.query.filter(
        ImageRecord.id.in_(record_ids),
        ImageRecord.user_id == current_user.id
    ).order_by(ImageRecord.created_at).all()
    
    if len(records) != len(record_ids):
        flash('Some selected records were not found or you do not have access to them.', 'danger')
        return redirect(url_for('main.history'))
    
    return render_template('compare_results.html', records=records)

@main.route('/export-personal-data')
@login_required
def export_personal_data():
    """Export user's personal data as CSV"""
    try:
        # Create CSV data
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Test ID', 'Image Filename', 'Prediction', 'Confidence', 
                        'Test Date', 'Risk Level'])
        
        # Write user's data
        records = ImageRecord.query.filter_by(user_id=current_user.id).order_by(ImageRecord.created_at).all()
        
        for record in records:
            risk_level = 'Low' if record.prediction_class == 'No_DR' else (
                'Medium' if record.prediction_class in ['Mild', 'Moderate'] else 'High'
            )
            
            writer.writerow([
                record.id,
                record.original_filename,
                record.prediction_class,
                f"{record.confidence:.2%}" if record.confidence else 'N/A',
                record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                risk_level
            ])
        
        # Create file-like object
        output.seek(0)
        
        # Create BytesIO from string
        mem = BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        return send_file(
            mem,
            as_attachment=True,
            download_name=f'my_dr_analysis_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )
        
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'danger')
        return redirect(url_for('main.history'))

# FAQ and Contact Pages
@main.route('/faq')
def faq():
    """Frequently Asked Questions"""
    return render_template('faq.html')

@main.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@main.route('/contact', methods=['POST'])
def contact_post():
    """Handle contact form submission"""
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        if not all([name, email, subject, message]):
            return jsonify({'success': False, 'error': 'Please fill in all fields.'}), 400
        
        # For AJAX requests, return JSON
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            # Here you would send an email to the admin
            # For now, we'll simulate the email sending
            # In production, you'd use the send_otp_email function or similar
            
            return jsonify({
                'success': True, 
                'message': 'Thank you for your message! We will get back to you soon.'
            })
        else:
            # For regular form submissions
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
            
    except Exception as e:
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('An error occurred while sending your message. Please try again.', 'danger')
            return redirect(url_for('main.contact'))

# API Endpoints for AJAX requests
@main.route('/api/delete-record/<int:record_id>', methods=['DELETE'])
@login_required
def api_delete_record(record_id):
    """API endpoint to delete a record"""
    try:
        record = ImageRecord.query.get_or_404(record_id)
        
        # Check if user owns this record or is admin
        if record.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Delete file from disk
        try:
            file_path = os.path.join(get_upload_folder(), record.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        
        # Delete from database
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@main.route('/api/record-stats/<int:record_id>')
@login_required
def api_record_stats(record_id):
    """API endpoint to get record statistics"""
    try:
        record = ImageRecord.query.get_or_404(record_id)
        
        # Check if user owns this record or is admin
        if record.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        stats = {
            'id': record.id,
            'prediction': record.prediction_class,
            'confidence': record.confidence,
            'upload_date': record.created_at.isoformat(),
            'filename': record.original_filename
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# New API Endpoints for Enhanced Functionality
@main.route('/api/notifications')
@login_required
def api_notifications():
    """API endpoint to get user notifications"""
    try:
        # Mock notifications for now - in a real app, you'd have a notifications table
        notifications = [
            {
                'id': 1,
                'message': 'Your analysis report for retinal image #123 is ready for download.',
                'created_at': datetime.now().isoformat(),
                'read': False,
                'type': 'report_ready'
            },
            {
                'id': 2,
                'message': 'New AI model update improves accuracy by 2%.',
                'created_at': datetime.now().isoformat(),
                'read': True,
                'type': 'system_update'
            }
        ]
        
        unread_count = sum(1 for n in notifications if not n['read'])
        
        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """API endpoint to mark notification as read"""
    try:
        # In a real app, you'd update the notification in the database
        # For now, just return success
        return jsonify({'success': True, 'message': 'Notification marked as read'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/user-analytics-data')
@login_required
def api_user_analytics_data():
    """API endpoint to get user analytics data for charts"""
    try:
        user_records = ImageRecord.query.filter_by(user_id=current_user.id).all()
        
        # Prepare data for different chart types
        prediction_counts = {}
        monthly_uploads = {}
        confidence_distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for record in user_records:
            # Count predictions
            prediction = record.prediction_class or 'Unknown'
            prediction_counts[prediction] = prediction_counts.get(prediction, 0) + 1
            
            # Monthly uploads
            month_key = record.created_at.strftime('%Y-%m')
            monthly_uploads[month_key] = monthly_uploads.get(month_key, 0) + 1
            
            # Confidence distribution
            if record.confidence:
                if record.confidence >= 0.8:
                    confidence_distribution['high'] += 1
                elif record.confidence >= 0.6:
                    confidence_distribution['medium'] += 1
                else:
                    confidence_distribution['low'] += 1
        
        return jsonify({
            'prediction_counts': prediction_counts,
            'monthly_uploads': monthly_uploads,
            'confidence_distribution': confidence_distribution,
            'total_analyses': len(user_records)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/comparison-data')
@login_required
def api_comparison_data():
    """API endpoint to get comparison data for selected records"""
    try:
        record_ids = request.args.get('ids', '').split(',')
        record_ids = [int(id.strip()) for id in record_ids if id.strip().isdigit()]
        
        if len(record_ids) < 2:
            return jsonify({'error': 'At least 2 records required for comparison'}), 400
        
        records = ImageRecord.query.filter(
            ImageRecord.id.in_(record_ids),
            ImageRecord.user_id == current_user.id
        ).all()
        
        comparison_data = []
        for record in records:
            comparison_data.append({
                'id': record.id,
                'filename': record.original_filename,
                'prediction': record.prediction_class,
                'confidence': record.confidence,
                'date': record.created_at.isoformat(),
                'image_url': f"/uploads/{record.filename}"
            })
        
        return jsonify({'records': comparison_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/system-info')
@login_required
def api_system_info():
    """API endpoint to get system information (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        total_users = User.query.count()
        total_analyses = ImageRecord.query.count()
        recent_analyses = ImageRecord.query.filter(
            ImageRecord.created_at >= datetime.now().replace(day=1)
        ).count()
        
        # Get prediction distribution
        prediction_stats = db.session.query(
            ImageRecord.prediction_class,
            db.func.count(ImageRecord.id)
        ).group_by(ImageRecord.prediction_class).all()
        
        return jsonify({
            'total_users': total_users,
            'total_analyses': total_analyses,
            'recent_analyses': recent_analyses,
            'prediction_stats': dict(prediction_stats)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/export-analytics')
@login_required
def api_export_analytics():
    """API endpoint to export user analytics as JSON"""
    try:
        user_records = ImageRecord.query.filter_by(user_id=current_user.id).all()
        
        analytics_data = {
            'user_info': {
                'name': current_user.name,
                'email': current_user.email,
                'export_date': datetime.now().isoformat()
            },
            'summary': {
                'total_analyses': len(user_records),
                'date_range': {
                    'first_analysis': min(r.created_at for r in user_records).isoformat() if user_records else None,
                    'last_analysis': max(r.created_at for r in user_records).isoformat() if user_records else None
                }
            },
            'analyses': [{
                'id': record.id,
                'filename': record.original_filename,
                'prediction': record.prediction_class,
                'confidence': record.confidence,
                'date': record.created_at.isoformat()
            } for record in user_records]
        }
        
        # Create JSON response
        response = Response(
            json.dumps(analytics_data, indent=2),
            mimetype='application/json'
        )
        response.headers['Content-Disposition'] = f'attachment; filename=analytics_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/create-public-link/<int:record_id>', methods=['POST'])
@login_required
def create_public_link(record_id):
    """Create a public link for a specific record"""
    record = ImageRecord.query.get_or_404(record_id)
    
    # Check if user owns this record or is admin
    if record.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Get consent from form data or JSON
        consent = False
        if request.is_json and request.json:
            consent = request.json.get('consent', False)
        else:
            consent = request.form.get('consent') == 'on'
            
        if not consent:
            return jsonify({'success': False, 'error': 'Consent is required for public sharing'}), 400
        
        from app.utils import auto_share_report_publicly
        public_url = auto_share_report_publicly(record.user, record, consent=True)
        
        if public_url:
            return jsonify({
                'success': True, 
                'url': public_url,
                'message': 'Public link created successfully!'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to create public link. Please try again later.'
            }), 500
            
    except Exception as e:
        print(f"Error creating public link: {e}")
        return jsonify({
            'success': False, 
            'error': 'An error occurred while creating the public link.'
        }), 500

@main.route('/delete_record/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    """Delete a record (fallback route for POST method)"""
    try:
        record = ImageRecord.query.get_or_404(record_id)
        
        # Check if user owns this record or is admin
        if record.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Delete file from disk
        try:
            upload_folder = get_upload_folder()
            file_path = os.path.join(upload_folder, record.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        
        # Delete from database
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/patient-trends')
@login_required
def patient_trends():
    """Display user's patient trends dashboard"""
    try:
        # Get user's records for trend analysis
        records = ImageRecord.query.filter_by(user_id=current_user.id)\
                                 .order_by(ImageRecord.created_at)\
                                 .all()
        
        if not records:
            flash('No data available for trends analysis. Upload some images first.', 'info')
            return redirect(url_for('main.index'))
        
        return render_template('patient_trends.html', records=records)
        
    except Exception as e:
        flash(f'Error loading patient trends: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@main.route('/model-performance')
@login_required
def model_performance():
    """Display model performance monitoring dashboard (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Get all records for model performance analysis
        all_records = ImageRecord.query.order_by(ImageRecord.created_at).all()
        
        return render_template('model_performance.html', records=all_records)
        
    except Exception as e:
        flash(f'Error loading model performance data: {str(e)}', 'danger')
        return redirect(url_for('main.admin'))

@main.route('/global-stats')
@login_required
def global_stats():
    """Display global statistics dashboard (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        return render_template('global_dashboard.html')
        
    except Exception as e:
        flash(f'Error loading global statistics: {str(e)}', 'danger')
        return redirect(url_for('main.admin'))

@main.route('/api/patient-trends-data')
@login_required
def api_patient_trends_data():
    """API endpoint to get patient trends data"""
    try:
        user_records = ImageRecord.query.filter_by(user_id=current_user.id)\
                                       .order_by(ImageRecord.created_at)\
                                       .all()
        
        # Prepare trend data
        timeline_data = []
        confidence_trends = []
        class_progression = []
        monthly_stats = {}
        
        for record in user_records:
            timeline_data.append({
                'date': record.created_at.isoformat(),
                'prediction_class': record.prediction_class or 'Unknown',
                'confidence': record.confidence or 0,
                'filename': record.filename
            })
            
            confidence_trends.append({
                'date': record.created_at.isoformat(),
                'confidence': record.confidence or 0
            })
            
            class_progression.append({
                'date': record.created_at.isoformat(),
                'class': record.prediction_class or 'Unknown'
            })
            
            # Monthly aggregation
            month_key = record.created_at.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'uploads': 0,
                    'avg_confidence': 0,
                    'predictions': {}
                }
            
            monthly_stats[month_key]['uploads'] += 1
            pred_class = record.prediction_class or 'Unknown'
            monthly_stats[month_key]['predictions'][pred_class] = \
                monthly_stats[month_key]['predictions'].get(pred_class, 0) + 1
        
        # Calculate average confidence per month
        for month in monthly_stats:
            month_records = [r for r in user_records 
                           if r.created_at.strftime('%Y-%m') == month]
            confidences = [r.confidence for r in month_records if r.confidence]
            monthly_stats[month]['avg_confidence'] = \
                sum(confidences) / len(confidences) if confidences else 0
        
        return jsonify({
            'timeline_data': timeline_data,
            'confidence_trends': confidence_trends,
            'class_progression': class_progression,
            'monthly_stats': monthly_stats,
            'total_records': len(user_records)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/model-performance-data')
@login_required
def api_model_performance_data():
    """API endpoint to get model performance data (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        all_records = ImageRecord.query.order_by(ImageRecord.created_at).all()
        
        # Calculate performance metrics
        daily_stats = {}
        confidence_distribution = {}
        class_distribution = {}
        drift_indicators = []
        
        for record in all_records:
            day_key = record.created_at.strftime('%Y-%m-%d')
            
            # Daily statistics
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    'total_predictions': 0,
                    'avg_confidence': 0,
                    'low_confidence_count': 0,
                    'predictions': {}
                }
            
            daily_stats[day_key]['total_predictions'] += 1
            
            # Confidence analysis
            confidence = record.confidence or 0
            if confidence < 0.7:
                daily_stats[day_key]['low_confidence_count'] += 1
            
            # Class distribution
            pred_class = record.prediction_class or 'Unknown'
            daily_stats[day_key]['predictions'][pred_class] = \
                daily_stats[day_key]['predictions'].get(pred_class, 0) + 1
            
            # Overall confidence distribution
            conf_bucket = 'low' if confidence < 0.6 else 'medium' if confidence < 0.8 else 'high'
            confidence_distribution[conf_bucket] = confidence_distribution.get(conf_bucket, 0) + 1
            
            # Overall class distribution
            class_distribution[pred_class] = class_distribution.get(pred_class, 0) + 1
        
        # Calculate average confidence per day
        for day in daily_stats:
            day_records = [r for r in all_records 
                          if r.created_at.strftime('%Y-%m-%d') == day]
            confidences = [r.confidence for r in day_records if r.confidence]
            daily_stats[day]['avg_confidence'] = \
                sum(confidences) / len(confidences) if confidences else 0
        
        # Detect potential model drift (simplified)
        recent_days = sorted(daily_stats.keys())[-7:]  # Last 7 days
        if len(recent_days) >= 2:
            recent_avg_conf = sum(daily_stats[day]['avg_confidence'] for day in recent_days) / len(recent_days)
            if recent_avg_conf < 0.7:
                drift_indicators.append({
                    'type': 'confidence_drop',
                    'severity': 'high' if recent_avg_conf < 0.6 else 'medium',
                    'message': f'Average confidence dropped to {recent_avg_conf:.2f} in recent days'
                })
        
        return jsonify({
            'daily_stats': daily_stats,
            'confidence_distribution': confidence_distribution,
            'class_distribution': class_distribution,
            'drift_indicators': drift_indicators,
            'total_predictions': len(all_records),
            'performance_summary': {
                'avg_confidence': sum(r.confidence or 0 for r in all_records) / len(all_records) if all_records else 0,
                'low_confidence_rate': sum(1 for r in all_records if (r.confidence or 0) < 0.7) / len(all_records) if all_records else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """API endpoint to get real-time dashboard statistics"""
    try:
        user_records = ImageRecord.query.filter_by(user_id=current_user.id).all()
        
        # Calculate current stats - Updated to match new class names: {0: 'Mild', 1: 'Moderate', 2: 'No_DR', 3: 'Proliferate_DR', 4: 'Severe'}
        total_images = len(user_records)
        no_dr_count = sum(1 for r in user_records if r.prediction_class == 'No_DR')
        mild_dr_count = sum(1 for r in user_records if r.prediction_class == 'Mild')
        moderate_dr_count = sum(1 for r in user_records if r.prediction_class == 'Moderate')
        severe_dr_count = sum(1 for r in user_records if r.prediction_class == 'Severe')
        proliferate_dr_count = sum(1 for r in user_records if r.prediction_class == 'Proliferate_DR')
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_records = [r for r in user_records if r.created_at >= thirty_days_ago]
        
        return jsonify({
            'total_images': total_images,
            'no_dr_count': no_dr_count,
            'mild_dr_count': mild_dr_count,
            'moderate_dr_count': moderate_dr_count,
            'recent_uploads': len(recent_records),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500