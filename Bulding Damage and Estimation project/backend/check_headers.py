import requests

# Use the inspection ID from the successful test run
inspection_id = "ba1a1f01-4" 
url = f"http://127.0.0.1:8000/api/report/damage/{inspection_id}"

try:
    print(f"Checking headers for {url}...")
    response = requests.get(url, stream=True)
    
    print(f"Status: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    
    response.close()
        
    if response.status_code == 404:
        print("\nInspection ID might be stale. Creating a new one first...")
        # Upload new image to get fresh ID
        upload_url = "http://127.0.0.1:8000/api/inspect/upload"
        with open("../sample_images/crack_sample.jpg", 'rb') as f:
            r = requests.post(upload_url, files={'file': f})
            new_id = r.json()['inspection']['inspection_id']
            print(f"New Inspection ID: {new_id}")
            
        url = f"http://127.0.0.1:8000/api/report/damage/{new_id}"
        # Use GET with stream=True to avoid downloading body but see headers
        response = requests.get(url, stream=True)
        print(f"Status: {response.status_code}")
        print("Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        response.close()

except Exception as e:
    print(f"Error: {e}")
