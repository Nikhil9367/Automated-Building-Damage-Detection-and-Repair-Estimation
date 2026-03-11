
import os
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import json
import sys

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "damage_model.h5")
INDICES_PATH = os.path.join(MODEL_DIR, "class_indices.json")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def verify():
    print("Verifying model...")
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return
    
    if not os.path.exists(INDICES_PATH):
        print(f"Error: Class indices not found at {INDICES_PATH}")
        return

    # Load Model
    try:
        model = load_model(MODEL_PATH)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Load Class Indices
    try:
        with open(INDICES_PATH, "r") as f:
            class_indices = json.load(f)
        # Invert to get index -> class name
        # The file saved as {'class': index}
        idx_to_class = {v: k for k, v in class_indices.items()}
        print(f"Class indices loaded: {class_indices}")
    except Exception as e:
        print(f"Error loading class indices: {e}")
        return

    # Find a test image
    # let's look for a random image in the dataset to test
    test_image_path = None
    for root, dirs, files in os.walk(DATASET_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                test_image_path = os.path.join(root, file)
                break
        if test_image_path:
            break
    
    if not test_image_path:
        print("No test image found in dataset to verify with.")
        # Try a known file from list_dir previously if dataset is empty?
        # previously saw "test image with spaces.jpg" in backend root
        potential_path = os.path.join(BASE_DIR, "test image with spaces.jpg")
        if os.path.exists(potential_path):
             test_image_path = potential_path

    if not test_image_path:
        print("Could not find any image to test.")
        return

    print(f"Testing with image: {test_image_path}")

    # Preprocess
    img = image.load_img(test_image_path, target_size=(224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = x / 255.0

    # Predict
    preds = model.predict(x)
    print(f"Raw predictions: {preds}")
    
    pred_class_idx = np.argmax(preds, axis=1)[0]
    pred_class_name = idx_to_class.get(pred_class_idx, "Unknown")
    confidence = np.max(preds)

    print(f"Predicted Class: {pred_class_name}")
    print(f"Confidence: {confidence:.4f}")
    print("Verification complete.")

if __name__ == "__main__":
    verify()
