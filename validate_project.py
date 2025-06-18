#!/usr/bin/env python3
"""
Clean and validate the enhanced Diabetic Retinopathy Detector project.
"""

import os
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("DIABETIC RETINOPATHY DETECTOR - PROJECT VALIDATION")
    print("=" * 60)
    
    # Check project structure
    required_files = [
        'config.py', 
        'requirements.txt',
        'run.py',
        'app/__init__.py',
        'app/models.py',
        'app/routes.py',
        'app/utils.py',
        'static/css/style.css',
        'static/js/main.js',
        'templates/base.html',
        'templates/index.html',
        'templates/login.html',
        'templates/register.html',
        'templates/upload.html',
        'templates/result.html',
        'templates/history.html',
        'templates/admin.html',
        'templates/analytics.html',
        'templates/compare_results.html',
        'templates/faq.html',
        'templates/contact.html',
        'templates/share_report.html'
    ]
    
    print("\n✓ Checking project structure...")
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✓ All required files present")
    
    # Check enhanced features
    print("\n✓ Checking enhanced features...")
    features_check = {
        'Dark Mode': check_dark_mode(),
        'Notifications': check_notifications(),
        'Comparison': check_comparison(),
        'Social Sharing': check_social_sharing(),
        'Analytics': check_analytics(),
        'Admin Panel': check_admin_panel(),
        'FAQ System': check_faq_system(),
        'Contact Form': check_contact_form()
    }
    
    for feature, status in features_check.items():
        status_icon = "✓" if status else "❌"
        print(f"{status_icon} {feature}: {'OK' if status else 'Missing'}")
    
    all_features_ok = all(features_check.values())
    
    print("\n" + "=" * 60)
    if all_features_ok:
        print("🎉 PROJECT VALIDATION SUCCESSFUL!")
        print("All enhanced features are properly implemented.")
        print("\nTo run the application:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Initialize database: python init_db.py")
        print("3. Run application: python run.py")
        print("4. Visit: http://localhost:5000")
    else:
        print("⚠️  Some features may need attention.")
        print("Check the items marked with ❌ above.")
    
    print("=" * 60)
    return all_features_ok

def check_dark_mode():
    """Check if dark mode is implemented."""
    css_file = Path('static/css/style.css')
    if not css_file.exists():
        return False
    
    css_content = css_file.read_text()
    return '.dark-mode' in css_content and 'darkModeToggle' in css_content

def check_notifications():
    """Check if notification system is implemented."""
    js_file = Path('static/js/main.js')
    if not js_file.exists():
        return False
    
    js_content = js_file.read_text()
    return 'initializeNotifications' in js_content and 'loadNotifications' in js_content

def check_comparison():
    """Check if comparison functionality is implemented."""
    history_file = Path('templates/history.html')
    if not history_file.exists():
        return False
    
    history_content = history_file.read_text()
    return 'record-checkbox' in history_content and 'compareBtn' in history_content

def check_social_sharing():
    """Check if social sharing is implemented."""
    share_file = Path('templates/share_report.html')
    if not share_file.exists():
        return False
    
    share_content = share_file.read_text()
    return 'social-share-btn' in share_content

def check_analytics():
    """Check if analytics is implemented."""
    analytics_file = Path('templates/analytics.html')
    if not analytics_file.exists():
        return False
    
    analytics_content = analytics_file.read_text()
    return 'analytics-chart' in analytics_content

def check_admin_panel():
    """Check if admin panel is enhanced."""
    admin_file = Path('templates/admin.html')
    if not admin_file.exists():
        return False
    
    admin_content = admin_file.read_text()
    return 'systemInfo' in admin_content and 'refreshSystemInfo' in admin_content

def check_faq_system():
    """Check if FAQ system is implemented."""
    faq_file = Path('templates/faq.html')
    if not faq_file.exists():
        return False
    
    faq_content = faq_file.read_text()
    return 'faqSearch' in faq_content and 'accordion' in faq_content

def check_contact_form():
    """Check if contact form is implemented."""
    contact_file = Path('templates/contact.html')
    if not contact_file.exists():
        return False
    
    contact_content = contact_file.read_text()
    return 'contactForm' in contact_content

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
