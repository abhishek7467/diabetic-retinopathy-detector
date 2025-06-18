from ultralytics import YOLO
from flask import current_app
import torch
import os

def predict(yolo_model, image_path):
    """Predict diabetic retinopathy class for given image using your custom model approach with confidence threshold"""
    if yolo_model is None:
        raise ValueError("Model not loaded. Please load the model first.")
    
    # Set confidence threshold
    CONFIDENCE_THRESHOLD = 0.60
    
    # Load and predict on the image - following your notebook pattern
    results = yolo_model(image_path, verbose=False, conf=0.50)
    result = results[0]

    # Get class names directly from result (like in your notebook)
    class_names = result.names
    print("name of the classes:", class_names)

    # Extract probabilities using your exact approach from notebook
    top_class = class_names[result.probs.top1]
    confidence = result.probs.top1conf.item()
    
    # Get all class probabilities
    probs = result.probs.data.cpu().numpy()
    
    # Print detailed predictions (following your style)
    print(f"\n🎯 Class Predictions:")
    for i, prob in enumerate(probs):
        class_name = class_names.get(i, f'Class {i}')
        print(f"  {i}: {class_name} - {prob:.6f} ({prob*100:.2f}%)")

    # Apply confidence threshold logic
    if confidence < CONFIDENCE_THRESHOLD:
        print(f"\n❌ No reliable detection - Confidence {confidence*100:.2f}% is below threshold ({CONFIDENCE_THRESHOLD*100:.0f}%)")
        return {
            'class_id': None,
            'class_name': 'No reliable detection',
            'confidence': confidence,
            'actual_confidence': confidence,
            'threshold_met': False,
            'threshold_value': CONFIDENCE_THRESHOLD,
            'message': f"Confidence {confidence*100:.2f}% is below threshold {CONFIDENCE_THRESHOLD*100:.0f}%",
            'predicted_class_only': {
                'class_name': top_class,
                'confidence': confidence
            }
        }
    else:
        print(f"\n✅ Final Prediction: {top_class} ({confidence*100:.2f}% confidence) - Above threshold")
        return {
            'class_id': int(result.probs.top1),
            'class_name': top_class,
            'confidence': confidence,
            'actual_confidence': confidence,
            'threshold_met': True,
            'threshold_value': CONFIDENCE_THRESHOLD,
            'message': f"Detected {top_class} with {confidence*100:.2f}% confidence",
            'predicted_class_only': {
                'class_name': top_class,
                'confidence': confidence
            }
        }

