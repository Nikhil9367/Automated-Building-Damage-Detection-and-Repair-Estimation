import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_chat():
    print("Testing Chatbot...")
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "message": "Hello, are you working?",
            "history": []
        })
        if response.status_code == 200:
            print("Chat Response:", response.json())
        else:
            print("Chat Failed:", response.status_code, response.text)
    except Exception as e:
        print("Chat Error:", e)

if __name__ == "__main__":
    test_chat()
