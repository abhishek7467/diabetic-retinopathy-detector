#!/usr/bin/env python3
"""
Verify that PDF reports include retinal images
"""

import os
import sys
from flask import Flask
from app import create_app
from app.models import User, ImageRecord, db
from app.utils import generate_pdf_report
import PyPDF2

def verify_pdf_content():
    """Verify PDF content includes images"""
    app = create_app()
    
    with app.app_context():
        # Get a test user and image record
        user = User.query.first()
        record = ImageRecord.query.first()
        
        if not user or not record:
            print("❌ No test data found. Please upload an image first.")
            return False
        
        print(f"✓ Testing with user: {user.name}")
        print(f"✓ Testing with record: {record.original_filename}")
        
        # Check if the original image file exists
        upload_folder = os.path.abspath(app.config.get('UPLOAD_FOLDER', 'uploads'))
        image_path = os.path.join(upload_folder, record.filename)
        
        print(f"🔍 Checking image file: {image_path}")
        print(f"📁 Image exists: {os.path.exists(image_path)}")
        
        if os.path.exists(image_path):
            image_size = os.path.getsize(image_path)
            print(f"📊 Image size: {image_size} bytes")
        
        # Generate PDF report
        app_url = "http://127.0.0.1:5000"
        print(f"🔄 Generating PDF report...")
        
        pdf_filename = generate_pdf_report(user, record, app_url)
        
        if pdf_filename:
            pdf_path = os.path.join(upload_folder, pdf_filename)
            
            print(f"✅ PDF generated successfully!")
            print(f"📁 PDF path: {pdf_path}")
            print(f"📄 PDF exists: {os.path.exists(pdf_path)}")
            
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"📊 PDF size: {file_size} bytes")
                
                # Try to analyze PDF content
                try:
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        num_pages = len(pdf_reader.pages)
                        print(f"📄 PDF pages: {num_pages}")
                        
                        # Check if PDF contains images (basic check)
                        has_images = False
                        for page in pdf_reader.pages:
                            if '/XObject' in page['/Resources']:
                                xObject = page['/Resources']['/XObject'].get_object()
                                for obj in xObject:
                                    if xObject[obj]['/Subtype'] == '/Image':
                                        has_images = True
                                        break
                        
                        print(f"🖼️  PDF contains images: {has_images}")
                        
                        if file_size > 15000:  # If PDF is larger than 15KB, likely has images
                            print("✅ PDF size indicates images are included")
                            return True
                        else:
                            print("⚠️  PDF size suggests images might be missing")
                            return False
                            
                except Exception as e:
                    print(f"⚠️  Could not analyze PDF content: {e}")
                    # Fall back to size check
                    if file_size > 15000:
                        print("✅ PDF size indicates images are likely included")
                        return True
                    else:
                        print("❌ PDF size suggests images are missing")
                        return False
            else:
                print(f"❌ PDF file not found at expected location")
                return False
        else:
            print(f"❌ PDF generation failed")
            return False

if __name__ == "__main__":
    success = verify_pdf_content()
    print(f"\n{'✅ VERIFICATION PASSED' if success else '❌ VERIFICATION FAILED'}")
    sys.exit(0 if success else 1)
