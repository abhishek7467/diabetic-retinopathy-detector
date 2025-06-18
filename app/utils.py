import os
import secrets
import smtplib
import requests
import json
import tempfile
import base64
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import uuid

# Handle phonenumbers import safely
try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_image(form_image, upload_folder):
    """Save uploaded image to disk with secure filename"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_image.filename)
    image_filename = random_hex + f_ext
    image_path = os.path.join(upload_folder, image_filename)
    
    # Resize image to reduce file size
    output_size = (800, 600)
    img = Image.open(form_image)
    img.thumbnail(output_size)
    img.save(image_path)
    
    return image_filename

def create_admin_user():
    """Create admin user if it doesn't exist"""
    from app.models import User, db
    
    admin_email = current_app.config['ADMIN_EMAIL']
    admin_password = current_app.config['ADMIN_PASSWORD']
    
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            name='Administrator',
            email=admin_email,
            is_admin=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")

def format_prediction_result(predictions):
    """Format YOLOv8 prediction results for display"""
    if not predictions:
        return None, 0.0, {}
    
    # Diabetic Retinopathy classes
    class_names =predictions.names
    
    # Get the prediction with highest confidence
    if hasattr(predictions, 'probs') and predictions.probs is not None:
        confidences = predictions.probs.data.cpu().numpy()
        predicted_class = confidences.argmax()
        confidence = float(confidences[predicted_class])
        
        # Create detailed results
        detailed_results = {}
        for i, conf in enumerate(confidences):
            detailed_results[class_names.get(i, f'Class {i}')] = float(conf)
        
        return class_names.get(predicted_class, f'Class {predicted_class}'), confidence, detailed_results
    
    return 'Unknown', 0.0, {}

    # Resize and normalize the image
    image = image.resize((640, 640))
    image_array = np.array(image) / 255.0
    return image_array

def classify_image(model, image):
    # Classify the image using the YOLOv8 model
    results = model(image)
    return results

def extract_prediction(results):
    # Extract the classification results from the model output
    predictions = results.pred[0]
    return predictions.tolist() if predictions is not None else []

def send_email(to, subject, body, is_html=False):
    """Send email using the configured SMTP server"""
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    username = current_app.config['MAIL_USERNAME']
    password = current_app.config['MAIL_PASSWORD']
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    
    # Attach the body with the correct MIME type
    if is_html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))
    
    # Connect to server and send
    try:
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()  # Secure the connection
        server.login(username, password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_otp_email(user, otp):
    """Send an email with OTP for password reset"""
    subject = "Password Reset OTP - Diabetic Retinopathy Detector"
    
    body = f"""
    Hello {user.name},
    
    You have requested to reset your password for the Diabetic Retinopathy Detector application.
    
    Your One-Time Password (OTP) is: {otp}
    
    This OTP is valid for 10 minutes. Please do not share it with anyone.
    
    If you did not request this password reset, please ignore this email.
    
    Thank you,
    Diabetic Retinopathy Detector Team
    """
    
    return send_email(user.email, subject, body)

def send_otp_sms(user, otp):
    """Send an SMS with OTP for password reset using various free SMS API options
    
    This implementation supports multiple SMS services:
    1. Twilio Verify (Free trial credits)
    2. Twilio SMS (Fallback)
    3. TextLocal (Free tier)
    4. D7SMS (Free trial)
    5. Fast2SMS (Free tier for India)
    
    Configure your preferred service in config.py
    """
    if not user.phone_number:
        return False
    
    sms_service = current_app.config.get('SMS_SERVICE', 'twilio')
    use_twilio_verify = current_app.config.get('USE_TWILIO_VERIFY', True)
    
    # Prepare message for services that need our own OTP
    if otp:
        message = f"Your OTP for password reset is: {otp}. Valid for 10 minutes. -Diabetic Retinopathy Detector"
    else:
        # For Twilio Verify, we don't need our own message
        message = None
        
    # If using Twilio Verify, we don't need to generate our own OTP
    if sms_service == 'twilio' and use_twilio_verify:
        # Twilio Verify (Most reliable, offers free trial credits)
        try:
            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
            verify_sid = current_app.config.get('TWILIO_VERIFY_SERVICE_SID')
            
            print(f"Using Twilio Verify for phone: {user.phone_number}")
            
            # First try using the Twilio Python SDK if available
            try:
                from twilio.rest import Client
                
                client = Client(account_sid, auth_token)
                if verify_sid:  # Type check to ensure verify_sid is not None
                    verification = client.verify.v2.services(verify_sid) \
                        .verifications \
                        .create(to=user.phone_number, channel='sms')
                        
                    print(f"Verification status: {verification.status}")
                    # We don't send our own OTP with Verify as Twilio handles it
                    # Instead we store verification SID for later verification
                    user.otp = verification.sid
                    return verification.sid is not None
                else:
                    print("Twilio Verify SID not configured")
                    return send_twilio_regular_sms(user, otp)
            except ImportError:
                # Use direct HTTP API if twilio package is not installed
                url = f"https://verify.twilio.com/v2/Services/{verify_sid}/Verifications"
                auth = (str(account_sid), str(auth_token))
                payload = {
                    "To": user.phone_number,
                    "Channel": "sms"
                }
                response = requests.post(url, data=payload, auth=auth)
                if response.status_code == 201:
                    response_data = response.json()
                    # Store verification SID instead of OTP
                    user.otp = response_data.get('sid')
                    return True
                else:
                    print(f"Twilio Verify API error: {response.status_code}")
                    print(response.text)
                    # Fallback to regular Twilio SMS if Verify fails
                    return send_twilio_regular_sms(user, otp)
                    
        except Exception as e:
            print(f"Twilio Verify error: {e}")
            # Try regular SMS as fallback
            return send_twilio_regular_sms(user, otp)
    
    # For services that need our own OTP message
    if not otp:
        print("Warning: No OTP provided for SMS service that requires it")
        return False
        
    # Handle various SMS services
    if sms_service == 'twilio':
        # Regular Twilio SMS
        return send_twilio_regular_sms(user, otp)
    elif sms_service == 'textlocal':
        # TextLocal (Offers free credits for testing)
        try:
            apikey = current_app.config.get('TEXTLOCAL_API_KEY')
            sender = current_app.config.get('SMS_SENDER_ID', 'DRRAPP')
            url = "https://api.textlocal.in/send/"
            
            # Format the phone number correctly for TextLocal (remove + and ensure proper format)
            phone = user.phone_number.replace("+", "")
            
            # Prepare the payload
            payload = {
                "apikey": apikey,
                "numbers": phone,
                "message": f"Your OTP for password reset is: {otp}. Valid for 10 minutes. -Diabetic Retinopathy Detector",
                "sender": sender
            }
            
            # Debug information
            print(f"Sending SMS via TextLocal to {phone}")
            
            # Send the request
            response = requests.post(url, data=payload)
            print(f"TextLocal response: {response.text}")
            
            # Parse the response
            response_data = response.json()
            success = response_data.get("status") == "success"
            
            if not success:
                print(f"TextLocal error: {response_data.get('errors', ['Unknown error'])}")
                
            return success
        except Exception as e:
            print(f"TextLocal SMS error: {e}")
            return False
    
    elif sms_service == 'd7sms':
        # D7SMS (Offers free trial SMS)
        try:
            api_token = current_app.config.get('D7SMS_API_TOKEN')
            sender = current_app.config.get('SMS_SENDER_ID', 'DRRAPP')
            url = "https://api.d7networks.com/messages/v1/send"
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [{
                    "channel": "sms",
                    "recipients": [user.phone_number.replace("+", "")],
                    "content": f"Your OTP for password reset is: {otp}. Valid for 10 minutes. -Diabetic Retinopathy Detector",
                    "msg_type": "text",
                    "data_coding": "text"
                }],
                "message_globals": {
                    "originator": sender,
                    "report_url": ""
                }
            }
            response = requests.post(url, json=payload, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"D7SMS error: {e}")
            return False
    
    # Fallback to email if SMS service fails or is not configured
    print(f"SMS service '{sms_service}' not configured or failed. Falling back to email.")
    if user.email:
        return send_otp_email(user, otp)
    return False
        
def validate_phone_number(phone_number):
    """Validate a phone number using the phonenumbers library
    
    Args:
        phone_number (str): Phone number with country code
        
    Returns:
        tuple: (is_valid, formatted_number)
    """
    if not phone_number:
        return False, None
        
    if not PHONENUMBERS_AVAILABLE:
        # Basic validation if phonenumbers is not available
        return len(phone_number) >= 10, phone_number
        
    try:
        # Parse the phone number - check if phonenumbers is available and imported
        if PHONENUMBERS_AVAILABLE:
            import phonenumbers  # Import locally to ensure it's available
            parsed = phonenumbers.parse(phone_number, None)
            
            # Check if it's valid
            if not phonenumbers.is_valid_number(parsed):
                return False, None
                
            # Format in international format
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164)
            return True, formatted
    except Exception as e:
        print(f"Phone validation error: {e}")
        return False, None
    
    # Fallback validation
    return len(phone_number) >= 10, phone_number
        
def send_otp(user, otp, method='email'):
    """Send OTP via the specified method"""
    if method == 'email':
        return send_otp_email(user, otp)
    elif method == 'phone':
        return send_otp_sms(user, otp)
    else:
        # Default to email if method is not recognized
        return send_otp_email(user, otp)

def send_twilio_regular_sms(user, otp):
    """Fallback function to send OTP via regular Twilio SMS"""
    try:
        account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
        message = f"Your OTP for password reset is: {otp}. Valid for 10 minutes. -Diabetic Retinopathy Detector"
        
        # Try with the SDK first
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            message_obj = client.messages.create(
                body=message,
                from_=from_number,
                to=user.phone_number
            )
            return message_obj.sid is not None
        except ImportError:
            # Use direct HTTP API if twilio package is not installed
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            auth = (str(account_sid), str(auth_token))
            payload = {
                "Body": message,
                "From": from_number,
                "To": user.phone_number
            }
            response = requests.post(url, data=payload, auth=auth)
            return response.status_code == 201
    except Exception as e:
        print(f"Twilio regular SMS error: {e}")
        return False

def verify_twilio_otp(user, code):
    """Verify the OTP using Twilio Verify API"""
    if not user.otp or not user.otp_created_at:
        return False
        
    # Check if we're using Twilio Verify (the OTP field contains a verification SID)
    if user.otp.startswith('VE'):
        try:
            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
            verify_sid = current_app.config.get('TWILIO_VERIFY_SERVICE_SID')
            verification_sid = user.otp
            
            # Try with the SDK first
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                if verify_sid:  # Type check to ensure verify_sid is not None
                    verification_check = client.verify.v2.services(verify_sid) \
                        .verification_checks \
                        .create(to=user.phone_number, code=code)
                        
                    is_valid = verification_check.status == "approved"
                    if is_valid:
                        # Clear OTP data after successful validation
                        user.otp = None
                        user.otp_created_at = None
                    return is_valid
                else:
                    print("Twilio Verify SID not configured")
                    return False
            except ImportError:
                # Use direct HTTP API if twilio package is not installed
                url = f"https://verify.twilio.com/v2/Services/{verify_sid}/VerificationCheck"
                auth = (str(account_sid), str(auth_token))
                payload = {
                    "To": user.phone_number,
                    "Code": code
                }
                response = requests.post(url, data=payload, auth=auth)
                if response.status_code == 200:
                    response_data = response.json()
                    is_valid = response_data.get('status') == "approved"
                    if is_valid:
                        # Clear OTP data after successful validation
                        user.otp = None
                        user.otp_created_at = None
                    return is_valid
                return False
        except Exception as e:
            print(f"Twilio Verify check error: {e}")
            return False
    
    # Fall back to regular OTP verification
    return user.otp == code

def generate_pdf_report(user, image_record, app_url=None):
    """Generate a comprehensive PDF report for the diabetic retinopathy detection results"""
    try:
        # Create a unique filename
        report_id = str(uuid.uuid4())[:8]
        pdf_filename = f"DR_Report_{user.name.replace(' ', '_')}_{report_id}.pdf"
        # Use absolute path to uploads folder
        upload_folder = os.path.join(current_app.root_path, current_app.config.get('UPLOAD_FOLDER', 'uploads'))
        pdf_path = os.path.join(upload_folder, pdf_filename)
        
        # Create the PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2C3E50'),
            alignment=1  # Center alignment
        )
        
        # Story to hold the content
        story = []
        
        # Title
        story.append(Paragraph("Diabetic Retinopathy Detection Report", title_style))
        story.append(Spacer(1, 20))
        
        # Patient Information Table
        patient_data = [
            ['Patient Information', ''],
            ['Name:', user.name],
            ['Email:', user.email],
            ['Phone:', user.phone_number or 'Not provided'],
            ['Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Report ID:', report_id]
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#ECF0F1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 20))
        
        # Test Results Section
        story.append(Paragraph("Diagnostic Results", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Results Table
        confidence_percentage = f"{image_record.confidence * 100:.1f}%" if image_record.confidence else "N/A"
        severity_color = get_severity_color(image_record.prediction_class)
        
        results_data = [
            ['Test Parameter', 'Result', 'Confidence'],
            ['Diabetic Retinopathy Classification', image_record.prediction_class or 'Unknown', confidence_percentage],
            ['Test Date', image_record.created_at.strftime('%B %d, %Y'), ''],
            ['Image File', image_record.original_filename, '']
        ]
        
        results_table = Table(results_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#FADBD8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(results_table)
        story.append(Spacer(1, 20))
        
        # Add the retinal image
        try:
            image_path = os.path.join(upload_folder, image_record.filename)
            if os.path.exists(image_path):
                story.append(Paragraph("Analyzed Retinal Image", styles['Heading2']))
                story.append(Spacer(1, 12))
                
                # Create ReportLab image from the uploaded file
                retinal_img = ReportLabImage(image_path, width=4*inch, height=3*inch)
                story.append(retinal_img)
                story.append(Spacer(1, 12))
                
                # Add image details
                story.append(Paragraph(f"<b>Image:</b> {image_record.original_filename}", styles['Normal']))
                story.append(Paragraph(f"<b>Upload Date:</b> {image_record.created_at.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
                story.append(Spacer(1, 20))
            else:
                # If image file doesn't exist, add a note
                story.append(Paragraph("Analyzed Retinal Image", styles['Heading2']))
                story.append(Paragraph(f"<i>Note: Original image file ({image_record.original_filename}) is not available for display.</i>", styles['Normal']))
                story.append(Spacer(1, 20))
        except Exception as e:
            print(f"Error adding retinal image to PDF: {e}")
            # Continue without the image if there's an error
            story.append(Paragraph("Analyzed Retinal Image", styles['Heading2']))
            story.append(Paragraph(f"<i>Note: Unable to display retinal image ({image_record.original_filename}).</i>", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Clinical Interpretation
        story.append(Paragraph("Clinical Interpretation", styles['Heading2']))
        interpretation = get_clinical_interpretation(image_record.prediction_class, image_record.confidence)
        story.append(Paragraph(interpretation, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Recommendations
        story.append(Paragraph("Recommendations", styles['Heading2']))
        recommendations = get_recommendations(image_record.prediction_class)
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # QR Code for report sharing
        if app_url:
            qr_img = generate_report_qr_code(app_url, report_id)
            if qr_img:
                story.append(Paragraph("Share this Report", styles['Heading2']))
                story.append(Paragraph("Scan the QR code below to view this report online:", styles['Normal']))
                story.append(Spacer(1, 12))
                story.append(qr_img)
        
        # Footer
        story.append(Spacer(1, 40))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#7F8C8D'),
            alignment=1
        )
        story.append(Paragraph("This report was generated by AI-powered Diabetic Retinopathy Detection System", footer_style))
        story.append(Paragraph("For medical advice, please consult with a qualified healthcare professional", footer_style))
        
        # Build the PDF
        doc.build(story)
        
        return pdf_filename
        
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None

def get_severity_color(prediction_class):
    """Get color code based on severity"""
    color_map = {
        'No_DR': '#2ECC71',          # Green
        'Mild': '#F39C12',           # Orange
        'Moderate': '#E67E22',       # Dark Orange
        'Severe': '#E74C3C',         # Red
        'Proliferate_DR': '#8E44AD'  # Purple
    }
    return color_map.get(prediction_class, '#95A5A6')

def get_clinical_interpretation(prediction_class, confidence):
    """Get clinical interpretation based on prediction"""
    interpretations = {
        'No_DR': "No signs of diabetic retinopathy detected. The retinal examination appears normal with no visible complications from diabetes.",
        'Mild': "Mild non-proliferative diabetic retinopathy detected. Early signs of retinal damage are present but vision is typically not affected at this stage.",
        'Moderate': "Moderate non-proliferative diabetic retinopathy detected. More blood vessels are blocked, affecting retinal circulation.",
        'Severe': "Severe non-proliferative diabetic retinopathy detected. Many blood vessels are blocked, depriving retinal areas of blood supply.",
        'Proliferate_DR': "Proliferative diabetic retinopathy detected. This is an advanced stage where new blood vessels grow abnormally in the retina."
    }
    
    base_interpretation = interpretations.get(prediction_class, "Unable to determine retinal condition from the provided image.")
    confidence_note = f" The AI model has {confidence*100:.1f}% confidence in this classification." if confidence else ""
    
    return base_interpretation + confidence_note

def get_recommendations(prediction_class):
    """Get recommendations based on prediction"""
    recommendations_map = {
        'No_DR': [
            "Continue regular eye examinations as recommended by your healthcare provider",
            "Maintain good blood sugar control",
            "Follow a healthy diet and exercise regularly",
            "Schedule annual dilated eye exams"
        ],
        'Mild': [
            "Increase frequency of eye examinations to every 6-12 months",
            "Focus on optimal blood sugar, blood pressure, and cholesterol control",
            "Discuss treatment options with your ophthalmologist",
            "Monitor for any changes in vision"
        ],
        'Moderate': [
            "Schedule immediate consultation with a retinal specialist",
            "Eye examinations every 3-6 months may be necessary",
            "Strict diabetes management is crucial",
            "Consider treatments to prevent progression"
        ],
        'Severe': [
            "Urgent consultation with a retinal specialist required",
            "Frequent monitoring and possible intervention needed",
            "Aggressive diabetes management essential",
            "Discuss laser treatment or other interventions"
        ],
        'Proliferate_DR': [
            "Immediate referral to retinal specialist is critical",
            "Prompt treatment required to prevent vision loss",
            "Consider laser photocoagulation or vitrectomy",
            "Very strict blood sugar control necessary"
        ]
    }
    
    return recommendations_map.get(prediction_class, [
        "Consult with a qualified ophthalmologist for proper diagnosis",
        "Maintain regular eye care and diabetes management"
    ])

def generate_report_qr_code(app_url, report_id):
    """Generate QR code for report sharing"""
    try:
        qr_url = f"{app_url}/shared-report/{report_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code to bytes
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, 'PNG')
        img_buffer.seek(0)
        
        # Create ReportLab image
        qr_reportlab_img = ReportLabImage(img_buffer, width=1.5*inch, height=1.5*inch)
        
        return qr_reportlab_img
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def create_analytics_chart(user_id):
    """Create analytics charts for user's test history"""
    try:
        # Import here to avoid circular imports
        from app.models import ImageRecord
        
        # Get user's image records
        records = ImageRecord.query.filter_by(user_id=user_id).order_by(ImageRecord.created_at).all()
        
        if len(records) < 2:
            return None
            
        # Prepare data
        dates = [record.created_at.date() for record in records]
        predictions = [record.prediction_class for record in records]
        confidences = [record.confidence * 100 if record.confidence else 0 for record in records]
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Prediction timeline
        ax1.plot(dates, range(len(dates)), 'o-', markersize=8, linewidth=2)
        ax1.set_title('Test Timeline', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Test Number')
        ax1.grid(True, alpha=0.3)
        
        # Confidence levels
        colors_map = {'No_DR': 'green', 'Mild': 'orange', 'Moderate': 'red', 
                     'Severe': 'darkred', 'Proliferate_DR': 'purple'}
        colors_list = [colors_map.get(pred, 'gray') for pred in predictions]
        
        ax2.bar(range(len(confidences)), confidences, color=colors_list, alpha=0.7)
        ax2.set_title('Confidence Levels by Test', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Confidence (%)')
        ax2.set_xlabel('Test Number')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer
        
    except Exception as e:
        print(f"Error creating analytics chart: {e}")
        return None

def send_report_via_email(user_email, pdf_path, recipient_email=None):
    """Send PDF report via email"""
    try:
        if not recipient_email:
            recipient_email = user_email
            
        subject = "Your Diabetic Retinopathy Detection Report"
        
        body = f"""
        Hello,
        
        Please find attached your diabetic retinopathy detection report.
        
        This report contains:
        - Detailed analysis results
        - Clinical interpretation
        - Recommendations for follow-up care
        
        Please consult with a qualified healthcare professional for medical advice.
        
        Best regards,
        Diabetic Retinopathy Detection Team
        """
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
            
        return send_email_with_attachment(recipient_email, subject, body, pdf_content, 
                                        os.path.basename(pdf_path), 'application/pdf')
        
    except Exception as e:
        print(f"Error sending report via email: {e}")
        return False

def send_email_with_attachment(to, subject, body, attachment_content, filename, mimetype):
    """Send email with attachment"""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        sender = current_app.config['MAIL_DEFAULT_SENDER']
        username = current_app.config['MAIL_USERNAME']
        password = current_app.config['MAIL_PASSWORD']
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachment
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {filename}')
        msg.attach(part)
        
        server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending email with attachment: {e}")
        return False

def create_public_report_html(user, image_record, app_url=None):
    """Create a public HTML report for sharing"""
    try:
        # Generate HTML content for public sharing  
        prediction_class = image_record.prediction_class or 'Unknown'
        confidence = f'{image_record.confidence * 100:.1f}%' if image_record.confidence else 'N/A'
        
        # Determine badge class
        if prediction_class == 'No_DR':
            badge_class = 'bg-success'
        elif prediction_class in ['Mild', 'Moderate']:
            badge_class = 'bg-warning'
        else:
            badge_class = 'bg-danger'
            
        # Get clinical interpretation and recommendations
        interpretation = get_clinical_interpretation(prediction_class, image_record.confidence)
        recommendations = get_recommendations(prediction_class)
        recommendations_html = ''.join([f'<li>{rec}</li>' for rec in recommendations])
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diabetic Retinopathy Analysis Report - {user.name}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; }}
        .report-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .severity-badge {{ font-size: 1.2em; padding: 0.5em 1em; }}
        .alert-medical {{ background-color: #fff3cd; border-color: #ffeaa7; color: #856404; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="report-header p-4 text-center">
            <h1><i class="bi bi-eye"></i> Diabetic Retinopathy Analysis Report</h1>
            <p class="lead">AI-Powered Medical Analysis Report</p>
        </div>
        
        <div class="container my-5">
            <div class="row">
                <div class="col-lg-8">
                    <div class="card shadow">
                        <div class="card-header bg-primary text-white">
                            <h3><i class="bi bi-clipboard-data"></i> Analysis Results</h3>
                        </div>
                        <div class="card-body">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h5>Patient Information</h5>
                                    <table class="table table-borderless">
                                        <tr><td><strong>Name:</strong></td><td>{user.name}</td></tr>
                                        <tr><td><strong>Test Date:</strong></td><td>{image_record.created_at.strftime('%B %d, %Y')}</td></tr>
                                        <tr><td><strong>Report Generated:</strong></td><td>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h5>Diagnostic Results</h5>
                                    <div class="text-center">
                                        <span class="badge severity-badge {badge_class}">
                                            {prediction_class}
                                        </span>
                                        <p class="mt-2">Confidence: {confidence}</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="alert alert-medical">
                                <h5><i class="bi bi-info-circle"></i> Clinical Interpretation</h5>
                                <p>{interpretation}</p>
                            </div>
                            
                            <div class="alert alert-info">
                                <h5><i class="bi bi-list-check"></i> Recommendations</h5>
                                <ul>
                                    {recommendations_html}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-4">
                    <div class="card shadow">
                        <div class="card-header bg-info text-white">
                            <h5><i class="bi bi-shield-check"></i> Important Notice</h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-warning">
                                <strong>Medical Disclaimer:</strong>
                                <p class="small">This is an AI-generated analysis for screening purposes only. 
                                Please consult with a qualified healthcare professional for proper medical advice and diagnosis.</p>
                            </div>
                            
                            <div class="alert alert-primary">
                                <strong>Privacy Notice:</strong>
                                <p class="small">This report has been shared publicly with patient consent for educational or consultation purposes.</p>
                            </div>
                            
                            <div class="text-center mt-3">
                                <p><small>Generated by:<br><strong>AI Diabetic Retinopathy Detection System</strong></small></p>
                                <p><small>Report ID: {str(uuid.uuid4())[:8]}</small></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <footer class="bg-dark text-white text-center py-3 mt-5">
        <p>&copy; 2024 Diabetic Retinopathy Detection System. This report is generated by AI technology.</p>
    </footer>
</body>
</html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"Error creating public HTML report: {e}")
        return None

def share_report_to_github_pages(user, image_record, github_token=None):
    """Share report to GitHub Pages (requires GitHub token)"""
    try:
        if not github_token:
            print("GitHub token not provided for public sharing")
            return None
            
        # Create HTML content
        html_content = create_public_report_html(user, image_record)
        if not html_content:
            return None
            
        # GitHub API configuration
        repo_owner = "medical-reports"  # You would need to create this organization
        repo_name = "diabetic-retinopathy-reports"
        
        # Generate unique filename
        report_filename = f"report_{user.name.replace(' ', '_').lower()}_{image_record.created_at.strftime('%Y%m%d_%H%M%S')}.html"
        
        # GitHub API URL
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{report_filename}"
        
        # Prepare request
        headers = {
            'Authorization': f'token {github_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'message': f'Add medical report for {user.name}',
            'content': base64.b64encode(html_content.encode()).decode(),
            'branch': 'main'
        }
        
        # Create file via GitHub API
        response = requests.put(api_url, headers=headers, json=data)
        
        if response.status_code == 201:
            # Return the public URL
            public_url = f"https://{repo_owner}.github.io/{repo_name}/{report_filename}"
            return public_url
        else:
            print(f"GitHub API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"Error sharing to GitHub Pages: {e}")
        return None

def share_report_to_netlify(user, image_record, netlify_token=None):
    """Share report to Netlify (requires Netlify token)"""
    try:
        if not netlify_token:
            print("Netlify token not provided for public sharing")
            return None
            
        # Create HTML content
        html_content = create_public_report_html(user, image_record)
        if not html_content:
            return None
            
        # Generate unique filename
        report_filename = f"report_{user.name.replace(' ', '_').lower()}_{image_record.created_at.strftime('%Y%m%d_%H%M%S')}.html"
        
        # Netlify API configuration
        site_id = "your-netlify-site-id"  # You would need to set this up
        api_url = f"https://api.netlify.com/api/v1/sites/{site_id}/files/{report_filename}"
        
        headers = {
            'Authorization': f'Bearer {netlify_token}',
            'Content-Type': 'text/html'
        }
        
        # Upload file to Netlify
        response = requests.put(api_url, headers=headers, data=html_content)
        
        if response.status_code in [200, 201]:
            # Return the public URL
            public_url = f"https://your-site-name.netlify.app/{report_filename}"
            return public_url
        else:
            print(f"Netlify API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        print(f"Error sharing to Netlify: {e}")
        return None

def create_temporary_public_share(user, image_record):
    """Create a temporary public share using file.io or similar service"""
    try:
        # Create HTML content
        html_content = create_public_report_html(user, image_record)
        if not html_content:
            return None
            
        # Generate unique filename
        report_filename = f"report_{user.name.replace(' ', '_').lower()}_{image_record.created_at.strftime('%Y%m%d_%H%M%S')}.html"
        
        # Save to temporary file
        temp_path = os.path.join(tempfile.gettempdir(), report_filename)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Upload to file.io (free temporary file sharing)
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': (report_filename, f, 'text/html')}
                response = requests.post('https://file.io', files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        # Clean up temp file
                        os.remove(temp_path)
                        return result.get('link')
        except Exception as e:
            print(f"Error with file.io: {e}")
        
        # Fallback: Try transfer.sh
        try:
            with open(temp_path, 'rb') as f:
                response = requests.put(f'https://transfer.sh/{report_filename}', data=f)
                
                if response.status_code == 200:
                    # Clean up temp file
                    os.remove(temp_path)
                    return response.text.strip()
        except Exception as e:
            print(f"Error with transfer.sh: {e}")
        
        # Clean up temp file if still exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return None
        
    except Exception as e:
        print(f"Error creating temporary public share: {e}")
        return None

def auto_share_report_publicly(user, image_record, consent=False):
    """Automatically share report to public platforms with user consent"""
    if not consent:
        print("Public sharing requires user consent")
        return None
        
    try:
        # Try different sharing methods in order of preference
        sharing_methods = [
            create_temporary_public_share,
            # share_report_to_github_pages,  # Requires token
            # share_report_to_netlify,       # Requires token
        ]
        
        for method in sharing_methods:
            try:
                public_url = method(user, image_record)
                if public_url:
                    print(f"Report shared publicly at: {public_url}")
                    return public_url
            except Exception as e:
                print(f"Sharing method {method.__name__} failed: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Error in auto public sharing: {e}")
        return None