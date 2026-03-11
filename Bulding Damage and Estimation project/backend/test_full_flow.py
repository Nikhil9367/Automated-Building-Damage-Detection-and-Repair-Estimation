import requests
import os
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
UPLOAD_URL = f"{BASE_URL}/api/inspect/upload"
REPORT_URL_TEMPLATE = f"{BASE_URL}/api/report/damage/{{}}"
IMG_PATH = "../sample_images/crack_sample.jpg"

def run_test():
    print("1. Testing Image Upload...")
    if not os.path.exists(IMG_PATH):
        print(f"Error: Sample image not found at {IMG_PATH}")
        return False

    inspection_id = None
    try:
        with open(IMG_PATH, 'rb') as f:
            files = {'file': f}
            response = requests.post(UPLOAD_URL, files=files)
        
        if response.status_code == 200:
            print("   Upload SUCCESS")
            data = response.json()
            inspection_id = data.get("inspection", {}).get("inspection_id")
            print(f"   Inspection ID: {inspection_id}")
        else:
            print(f"   Upload FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   Upload EXCEPTION: {e}")
        return False

    if not inspection_id:
        print("   Error: No inspection ID returned.")
        return False

    print("\n2. Testing Report Generation...")
    report_url = REPORT_URL_TEMPLATE.format(inspection_id)
    try:
        response = requests.get(report_url)
        if response.status_code == 200:
            print("   Report Generation SUCCESS")
            # Verify it's a PDF
            if response.headers.get('content-type') == 'application/pdf':
                print("   Content-Type is correct (application/pdf)")
                with open(f"test_report_{inspection_id}.pdf", "wb") as f:
                    f.write(response.content)
                print(f"   Saved report to test_report_{inspection_id}.pdf")
                return True
            else:
                print(f"   Error: Unexpected content type: {response.headers.get('content-type')}")
                return False
        else:
            print(f"   Report Generation FAILED: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   Report Generation EXCEPTION: {e}")
        return False

if __name__ == "__main__":
    if run_test():
        print("\nAll systems GO! Project is working.")
        sys.exit(0)
    else:
        print("\nSomething is broken.")
        sys.exit(1)
