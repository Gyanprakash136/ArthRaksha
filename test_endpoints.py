import json
from fastapi.testclient import TestClient
from arthraksha.api.main import app

client = TestClient(app)

endpoints = [
    "/dashboard/metrics",
    "/dashboard/cases",
    "/dashboard/insights",
    "/dashboard/promise-tracker"
]

for endpoint in endpoints:
    print(f"--- {endpoint} ---")
    response = client.get(endpoint)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2)[:500] + "\n...[truncated if long]")
    else:
        print(f"ERROR {response.status_code}: {response.text}")

