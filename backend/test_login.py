import requests
import json
import sys

url = 'https://successcore-api.onrender.com/api/v1/users/login'
headers = {
    'Content-Type': 'application/json',
    'Origin': 'https://omnius-six.vercel.app'
}
data = {
    "email": "admin@successcore.com",
    "password": "admin",
    "tenant_id": "acme_corp"
}

print(f"POSTing to {url}")
try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    print("Response JSON:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
