import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key_change_in_production'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///retinopatia.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    YOLOV8_MODEL_PATH = '/media/abhisekhkumar/532f0f5d-32d6-4a7c-9464-0aa27dbfb9b8/Tutorials/retinopatia_project/RD_project/diabetic-retinopathy-detector/yolo_model/best.pt'    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Allowed image file extensions
    
    # Pagination settings
    RECORDS_PER_PAGE = 10
    
    # Admin credentials (for demo purposes - use proper auth in production)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@retinopatia.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Email configuration for password reset
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-email@gmail.com'  # Replace in production
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-app-password'  # Replace in production
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@retinopatia.com'
    
    # OTP settings
    OTP_VALID_WINDOW = 600  # OTP valid for 10 minutes
    
    # SMS service configuration
    SMS_SERVICE = os.environ.get('SMS_SERVICE') or 'twilio'  # Options: 'twilio', 'textlocal', 'd7sms', 'fast2sms'
    SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID') or 'DRRAPP'
    
    # Twilio settings (free trial available)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID') or ''
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN') or ''
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER') or '+15551234567'
    TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID') or ''
    USE_TWILIO_VERIFY = os.environ.get('USE_TWILIO_VERIFY', 'True').lower() in ('true', '1', 't')  # Set to True to use Twilio Verify instead of regular SMS
    
    # TextLocal settings (free credits available for India)
    # You can sign up for a free account at https://www.textlocal.in/
    # And get free test credits
    TEXTLOCAL_API_KEY = os.environ.get('TEXTLOCAL_API_KEY') or ''
    
    # Fast2SMS settings (free for testing in India)
    # Sign up at https://www.fast2sms.com/
    FAST2SMS_API_KEY = os.environ.get('FAST2SMS_API_KEY') or 'your_fast2sms_api_key'
    
    # D7SMS settings (free trial available)
    D7SMS_API_TOKEN = os.environ.get('D7SMS_API_TOKEN') or 'your_d7sms_api_token'
