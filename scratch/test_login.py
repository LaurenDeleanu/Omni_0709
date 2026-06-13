import urllib.request, json, sys
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/users/login', 
    data=json.dumps({'email':'admin@acme.com', 'password':'admin'}).encode(), 
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP ERROR:', e.code)
    print(e.read().decode())
except Exception as e:
    print('OTHER ERROR:', e)
