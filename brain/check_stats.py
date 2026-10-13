import requests

res = requests.post("http://localhost:8000/api/auth/login", json={"username": "admin", "password": "adminpassword123"})
token = res.json()["access_token"]

audit_res = requests.get("http://localhost:8000/api/audit?limit=20", headers={"Authorization": f"Bearer {token}"})
audits = audit_res.json()
print("Audits count:", len(audits))
actions = [a for a in audits if "REMEDIATION" in a.get("action", "") or "APPROVAL" in a.get("action", "")]
for a in actions:
    print(a.get("action"), a.get("actor"), a.get("details"))
