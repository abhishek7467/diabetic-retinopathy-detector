#!/usr/bin/env python3
"""
Script to run the Flask application
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting Diabetic Retinopathy Detector application...")
    app.run(debug=True, port=9590)
    print("Application stopped.")
