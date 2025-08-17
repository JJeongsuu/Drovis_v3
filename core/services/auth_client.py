import requests
API = "http://127.0.0.1:8000"  # app.py가 로컬 서버 자동 실행

def send_code(email: str) -> None:
    r = requests.post(f"{API}/auth/send-code", json={"email": email})
    r.raise_for_status()

def verify_code(email: str, code: str) -> str:
    r = requests.post(f"{API}/auth/verify-code", json={"email": email, "code": code})
    r.raise_for_status()
    return r.json()["verification_token"]

def register(username: str, email: str, password: str, verification_token: str) -> bool:
    r = requests.post(f"{API}/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "verification_token": verification_token
    })
    r.raise_for_status()
    return r.json()["ok"]
