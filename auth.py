import os
import json
from datetime import datetime, timedelta
import requests

KIWOOM_HOST = "https://api.kiwoom.com"
TOKEN_CACHE_FILE = "kiwoom_token.json"
APPKEY_FILE = "52193434_appkey.txt"
SECRETKEY_FILE = "52193434_secretkey.txt"

def load_credentials():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    appkey_path = os.path.join(base_dir, APPKEY_FILE)
    secretkey_path = os.path.join(base_dir, SECRETKEY_FILE)

    if not os.path.exists(appkey_path) or not os.path.exists(secretkey_path):
        raise FileNotFoundError("키움 API 키 파일(appkey/secretkey)을 찾을 수 없습니다.")

    with open(appkey_path, "r", encoding="utf-8") as f:
        appkey = f.read().strip()
    with open(secretkey_path, "r", encoding="utf-8") as f:
        secretkey = f.read().strip()

    return appkey, secretkey

def request_new_token(appkey: str, secretkey: str) -> dict:
    url = f"{KIWOOM_HOST}/oauth2/token"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "AU10001"
    }
    payload = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "secretkey": secretkey
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    body = resp.json()

    token = body.get("token")
    if not token:
        raise ValueError(f"키움 API 토큰 발급 실패: {body}")

    # 만료 일시 파싱 (예: 2026-10-04 15:30:00 또는 ISO 포맷 대응)
    expires_dt_str = body.get("expires_dt")
    token_data = {
        "access_token": token,
        "token_type": body.get("token_type", "Bearer"),
        "expires_dt": expires_dt_str,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(base_dir, TOKEN_CACHE_FILE)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)

    return token_data

def get_token() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(base_dir, TOKEN_CACHE_FILE)

    appkey, secretkey = load_credentials()

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            token = data.get("access_token")
            expires_dt_str = data.get("expires_dt")
            if token and expires_dt_str:
                # 안전하게 10분 여유 두고 만료 확인 (YYYYMMDDHHMMSS 또는 YYYY-MM-DD HH:MM:SS)
                try:
                    if len(expires_dt_str) == 14:
                        expires_dt = datetime.strptime(expires_dt_str, "%Y%m%d%H%M%S")
                    else:
                        expires_dt = datetime.strptime(expires_dt_str, "%Y-%m-%d %H:%M:%S")
                    
                    if datetime.now() + timedelta(minutes=10) < expires_dt:
                        # print("✅ 기존 토큰 캐시 재사용")
                        return token
                except Exception:
                    pass
        except Exception:
            pass  # 캐시 읽기 실패 시 새로 발급

    print("🔄 키움 OpenAPI 새 토큰 발급 중...")
    token_data = request_new_token(appkey, secretkey)
    print("✅ 키움 토큰 발급 성공!")
    return token_data["access_token"]

if __name__ == "__main__":
    t = get_token()
    print("발급된 토큰 (앞 10자리):", t[:10] + "...")
