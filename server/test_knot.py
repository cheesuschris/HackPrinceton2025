import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('KNOT_CLIENT_ID')
SECRET = os.getenv('KNOT_SECRET')

print(f"Testing with Client ID: {CLIENT_ID[:10]}...")

credentials = f"{CLIENT_ID}:{SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

api_url = 'https://development.knotapi.com/session/create'
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json',
    'Knot-Version': '2.0'
}

payload = {
    'type': 'transaction_link',
    'external_user_id': 'test_user_123',
    'entry_point': 'carbon_tracking'
}

print(f"\nCalling: {api_url}")
print(f"Payload: {payload}\n")

try:
    response = requests.post(api_url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}\n")
    
    if response.status_code == 200:
        data = response.json()
        # Check for both 'session_id' and 'session' keys
        session_id = data.get('session_id') or data.get('session')
        
        if session_id:
            print("✅ SUCCESS! Session created:")
            print(f"Session ID: {session_id}")
        else:
            print("❌ ERROR: No session_id in response")
            print(f"Response keys: {list(data.keys())}")
    else:
        print("❌ ERROR: Failed to create session")
        
except Exception as e:
    print(f"❌ EXCEPTION: {str(e)}")