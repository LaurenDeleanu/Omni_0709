#!/usr/bin/env python3
import os
import requests
import sys
import json

def main():
    api_key = os.environ.get("RENDER_API_KEY")
    if not api_key:
        print("Error: RENDER_API_KEY environment variable is not set.")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    
    if action == "list":
        resp = requests.get("https://api.render.com/v1/services", headers=headers)
        if resp.status_code == 200:
            services = resp.json()
            for s in services:
                print(f"Service: {s['service']['name']} ({s['service']['id']}) - Type: {s['service']['type']} - Suspended: {s['service']['suspended']}")
        else:
            print(f"Error: {resp.status_code} {resp.text}")
    elif action == "deploys" and len(sys.argv) > 2:
        service_id = sys.argv[2]
        resp = requests.get(f"https://api.render.com/v1/services/{service_id}/deploys", headers=headers)
        if resp.status_code == 200:
            deploys = resp.json()
            for d in deploys[:5]:
                print(f"Deploy ID: {d['deploy']['id']} - Status: {d['deploy']['status']} - Created: {d['deploy']['createdAt']}")
        else:
            print(f"Error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()
