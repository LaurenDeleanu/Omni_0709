import requests
import json

base_url = "http://127.0.0.1:10000/api/v1"

print("Logging in...")
try:
    res = requests.post(f"{base_url}/users/login", json={
        "email": "lauren.deleanu@gmail.com",
        "password": "admin",
        "tenant_id": "acme_corp"
    })
    print("Login Status:", res.status_code)
    
    if res.status_code == 200:
        data = res.json()
        token = data.get("accessToken")
        
        print("\nFetching dashboard...")
        dash_res = requests.get(f"{base_url}/reports/dashboard", headers={
            "Authorization": f"Bearer {token}"
        })
        print("Dashboard Status:", dash_res.status_code)
        try:
            print("Dashboard Data:", json.dumps(dash_res.json(), indent=2))
        except:
            print("Dashboard Response:", dash_res.text)
    else:
        print("Login Error:", res.text)
except Exception as e:
    print("Request failed:", str(e))
