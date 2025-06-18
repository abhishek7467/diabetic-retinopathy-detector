# Diabetic Retinopathy Detector

This project is a web application for detecting and classifying stages of diabetic retinopathy using a YOLOv8 classification model. The application allows users to upload images of their retinas, which are then processed to identify the presence and stage of diabetic retinopathy.

## Features

- User authentication for secure access
- Image upload functionality
- Real-time classification of diabetic retinopathy stages
- Display of results with uploaded images
- Password reset functionality with OTP verification (email and SMS)
- Secure logout functionality
- Multi-channel OTP delivery (email and phone)

## Project Structure

```
diabetic-retinopathy-detector
├── app
│   ├── __init__.py
│   ├── routes.py
│   ├── models.py
│   └── utils.py
├── static
│   ├── css
│   │   └── style.css
│   └── js
│   │   └── main.js
├── templates
│   ├── base.html
│   ├── index.html
│   └── results.html
├── models
│   └── yolov8_classifier.py
├── uploads
├── config.py
├── requirements.txt
├── app.py
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd diabetic-retinopathy-detector
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up the database and any necessary configurations in `config.py`.
   Change the Yolo model path in config.py file like     YOLOV8_MODEL_PATH = '/media/abhisekhkumar/532f0f5d-32d6-4a7c-9464-0aa27dbfb9b8/Tutorials/retinopatia_project/RD_project/diabetic-retinopathy-detector/yolo_model/best.pt'    


5. Configure OTP settings for email and SMS functionality:
   ```
   # Email settings in config.py
   MAIL_SERVER = 'smtp.gmail.com'  # Or your preferred SMTP server
   MAIL_PORT = 587
   MAIL_USE_TLS = True
   MAIL_USERNAME = 'your-email@gmail.com'  # Your email address
   MAIL_PASSWORD = 'your-app-password'     # Your app password (for Gmail)
   MAIL_DEFAULT_SENDER = 'noreply@retinopatia.com'
   
   # SMS service configuration (choose one of the options below)
   SMS_SERVICE = 'twilio'  # Options: 'twilio', 'textlocal', 'd7sms'
   
   # Twilio settings (sign up at https://www.twilio.com/try-twilio for free trial)
   TWILIO_ACCOUNT_SID = 'your_twilio_account_sid' 
   TWILIO_AUTH_TOKEN = 'your_twilio_auth_token'
   TWILIO_PHONE_NUMBER = 'your_twilio_phone_number'
   ```
   
   Notes:
   - For Gmail, you will need to:
     - Enable 2-Step Verification for your Google account
     - Generate an App Password (Google Account → Security → App Passwords)
     - Use this App Password instead of your regular password
     
   - For SMS functionality:
     1. Create a free Twilio account (https://www.twilio.com/try-twilio)
     2. Get your Account SID, Auth Token, and a trial phone number
     3. Set SMS_SERVICE = 'twilio' in config.py
     4. Add your Twilio credentials to config.py

## Usage

1. Run the application:
   ```
   python app.py
   ```

2. Open your web browser and go to `http://127.0.0.1:5000`.

3. Upload an image of the retina to get the classification results.

4. Use the password reset functionality:
   - Click on "Forgot your password?" on the login page
   - Choose your preferred verification method (email or phone)
   - Enter your registered email address or phone number
   - Check your email or phone for the OTP code
   - Enter the OTP to verify your identity
   - Create a new password
   
   Note: You must have registered your phone number in your profile to use the SMS OTP option

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.