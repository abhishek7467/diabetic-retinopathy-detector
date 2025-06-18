from datetime import datetime, timedelta
import random
import string
import jwt
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer

# Create db instance - this will be initialized in app.py
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp = db.Column(db.String(6), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)
    otp_method = db.Column(db.String(10), nullable=True)  # 'email' or 'phone'
    
    # Relationship with ImageRecord
    images = db.relationship('ImageRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Flask-Login required methods
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_otp(self, method='email'):
        """Generate a 6-digit OTP
        
        Args:
            method (str): Method to send OTP ('email' or 'phone')
        """
        otp = ''.join(random.choices(string.digits, k=6))
        self.otp = otp
        self.otp_created_at = datetime.utcnow()
        self.otp_method = method
        return otp
        
    def verify_otp(self, otp):
        """Verify OTP is valid and not expired
        
        This method handles both standard OTPs and Twilio Verify SIDs
        """
        from app.utils import verify_twilio_otp
        
        if not self.otp or not self.otp_created_at:
            return False
            
        # Check if we're using Twilio Verify (otp field contains a verification SID)
        if self.otp_method == 'phone' and self.otp.startswith('VE'):
            return verify_twilio_otp(self, otp)
            
        # Standard OTP verification
        # Check if OTP is valid within the time window
        expiration_time = self.otp_created_at + timedelta(seconds=current_app.config['OTP_VALID_WINDOW'])
        if datetime.utcnow() > expiration_time:
            return False
            
        # Verify OTP
        is_valid = self.otp == otp
        if is_valid:
            # Clear OTP after successful validation
            self.otp = None
            self.otp_created_at = None
            
        return is_valid
        
    def generate_reset_token(self):
        """Generate a password reset token"""
        payload = {
            'user_id': self.id,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def verify_reset_token(token):
        """Verify a password reset token"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except:
            return None
        return User.query.get(user_id)
    
    def __repr__(self):
        return f'<User {self.email}>'

class ImageRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prediction_class = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    prediction_details = db.Column(db.Text, nullable=True)  # JSON string of all class probabilities
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ImageRecord {self.filename} - {self.prediction_class}>'