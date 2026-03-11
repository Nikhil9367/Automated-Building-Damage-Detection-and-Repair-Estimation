import requests
import json

UPLOAD_URL = "http://127.0.0.1:8000/api/inspect/upload"
IMG_PATH = "../sample_images/crack_sample.jpg"

def check_json():
    try:
        with open(IMG_PATH, 'rb') as f:
            files = {'file': f}
            response = requests.post(UPLOAD_URL, files=files)
            
        if response.status_code == 200:
            data = response.json()
            pr = data.get("inspection", {}).get("result", {}).get("post_repair_life_expectancy", {})
            print("Post Repair Life Keys:", pr.keys())
            print("Age After Repair:", pr.get("estimated_structure_age_after_repair"))
            print("Life Extension:", pr.get("life_extension_years"))
            
        else:
            print("Failed:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_json()
