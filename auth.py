# auth.py
import os
import hmac
import hashlib
import json
import urllib.parse
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import SessionLocal  # Ensure your database.py defines SessionLocal and engine
from models import User         # Your User model defined in models.py

load_dotenv()

router = APIRouter()

# Load BOT_TOKEN and TEST_MODE flag from .env
BOT_TOKEN = os.getenv("BOT_TOKEN", "8073824494:AAHQlUVQpvlzBFX_5kfjD02tcdRkjGTGBeI")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

if TEST_MODE:
    print("[TEST MODE] Enabled. Test bypass for auth is active.")
else:
    print("[PRODUCTION MODE] Test bypass disabled. Full HMAC verification active.")

print("BOT_TOKEN:", BOT_TOKEN)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_telegram_auth(init_data: str) -> dict:
    """
    Verify Telegram initData and return user info if valid; otherwise return {}.
    In TEST_MODE, if the hash equals "fakehash", bypass HMAC verification.
    """
    try:
        print("[DEBUG] Received init_data:", init_data)
        # Parse the initData string into key/value pairs
        parsed = dict(pair.split("=", 1) for pair in init_data.split("&") if "=" in pair)
        print("[DEBUG] Parsed data:", parsed)
        hash_value = parsed.pop("hash", None)
        print("[DEBUG] Extracted hash:", hash_value)
        if not hash_value:
            print("[DEBUG] No hash found in init_data.")
            return {}

        # If TEST_MODE is enabled and the hash is "fakehash", bypass HMAC verification.
        if TEST_MODE and hash_value == "fakehash":
            print("[DEBUG] TEST_MODE enabled and fakehash detected, bypassing HMAC check.")
            if "user" in parsed:
                user_json = urllib.parse.unquote(parsed["user"])
                print("[DEBUG] Decoded user JSON:", user_json)
                user_obj = json.loads(user_json)
                print("[DEBUG] Parsed user object:", user_obj)
                return user_obj
            return parsed

        # Build data_check_string by sorting keys alphabetically
        data_check_string = "\n".join(f"{k}={parsed[k]}" for k in sorted(parsed.keys()))
        print("[DEBUG] data_check_string:", data_check_string)

        # Calculate the secret key from BOT_TOKEN
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        print("[DEBUG] Secret key (SHA256 of BOT_TOKEN):", secret_key)

        # Calculate HMAC using SHA256
        computed_hash = hmac.new(secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256).hexdigest()
        print("[DEBUG] Computed HMAC:", computed_hash)

        if computed_hash != hash_value:
            print("[DEBUG] HMAC verification failed.")
            return {}

        # Decode and parse the user information if present
        if "user" in parsed:
            user_json = urllib.parse.unquote(parsed["user"])
            print("[DEBUG] Decoded user JSON:", user_json)
            user_obj = json.loads(user_json)
            print("[DEBUG] Parsed user object:", user_obj)
            return user_obj

        print("[DEBUG] No user parameter found; returning parsed data.")
        return parsed
    except Exception as e:
        print(f"Error verifying Telegram auth data: {e}")
        return {}

@router.post("/auth/telegram")
async def telegram_auth(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint for mini app auth.
    Expects a JSON body: { "initData": "<telegram init data string>" }.
    Verifies the auth data and then either updates the user record or cross-references stored user info using the Telegram user ID.
    """
    body = await request.json()
    print("[DEBUG] /auth/telegram endpoint called with body:", body)
    init_data = body.get("initData", "")
    if not init_data:
        print("[DEBUG] No initData provided in request body.")
        return JSONResponse({"success": False, "error": "No initData provided"}, status_code=400)

    user_info = verify_telegram_auth(init_data)
    if not user_info:
        print("[DEBUG] Telegram auth verification failed.")
        return JSONResponse({"success": False, "error": "Invalid auth data"}, status_code=403)

    # Use Telegram user ID as the unique identifier (convert to string)
    telegram_id = str(user_info.get("id"))
    if not telegram_id:
        print("[DEBUG] User ID missing in auth data.")
        return JSONResponse({"success": False, "error": "User ID missing"}, status_code=400)

    # Cross-reference or update the stored user record
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    username = user_info.get("username") or user_info.get("first_name", "Telegram User")
    photo_url = user_info.get("photo_url") or "/images/default_avatar.png"
    if user:
        user.username = username  # Optionally update if changed
        user.photo_url = photo_url
        print(f"[DEBUG] Existing user updated in DB: {telegram_id} - {username}")
    else:
        user = User(
            telegram_id=telegram_id,
            username=username,
            photo_url=photo_url
        )
        db.add(user)
        print(f"[DEBUG] New user created in DB: {telegram_id} - {username}")
    db.commit()
    db.refresh(user)
    print("[DEBUG] Auth successful. User stored in DB:", user.telegram_id, user.username)
    return {"success": True, "user": {"id": user.id, "telegram_id": user.telegram_id, "username": user.username, "photo_url": user.photo_url}}

@router.post("/auth/logout")
async def logout():
    """
    Simple logout endpoint. In production, invalidate sessions/tokens as needed.
    """
    print("[DEBUG] /auth/logout called.")
    return {"success": True}
