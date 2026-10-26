import httpx
import sys

url = "http://127.0.0.1:8000/index"
payload = {
    "directory_path": "C:/Users/shemg/.gemini/antigravity/scratch/developer-research-assistant"
}

print(f"Sending index request to {url}...")
try:
    response = httpx.post(url, json=payload, timeout=30.0)
    print("Response Status Code:", response.status_code)
    print("Response JSON:", response.json())
    if response.status_code != 200:
        sys.exit(1)
except Exception as e:
    print("Connection failed:", e)
    sys.exit(1)
