import requests
import os

# Create a dummy image file
# Use a real image file
dummy_img = "../sample_images/crack_sample.jpg"

url = "http://127.0.0.1:8000/api/inspect/upload"
try:
    print(f"Sending POST request to {url}...")
    with open(dummy_img, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
finally:
    try:
        if os.path.exists(dummy_img):
            # os.remove(dummy_img)
            pass
    except Exception as e:
        print(f"Could not remove dummy file: {e}")
