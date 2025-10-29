import os
from flask import Blueprint, redirect, request, session, url_for, jsonify
from authlib.integrations.flask_client import OAuth
from supabase import create_client
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import requests
from google.oauth2.credentials import Credentials  # ✅ NEW IMPORT

# ---------- Setup ----------
auth_bp = Blueprint("auth", __name__)
load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def supabase_table(table_name: str):
    return supabase.table(table_name)

# Encryption for tokens
fernet = Fernet(os.getenv("ENCRYPTION_KEY").encode())

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

# ---------- Token refresh ----------
def refresh_access_token(email: str):
    row = supabase_table("user_tokens").select("*").eq("email", email).execute().data
    if not row:
        raise Exception("No tokens found for this user")
    row = row[0]
    refresh_token = decrypt_token(row["refresh_token"])
    data = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post("https://oauth2.googleapis.com/token", data=data)
    if response.status_code != 200:
        raise Exception(f"Failed to refresh access token: {response.text}")
    tokens = response.json()
    supabase_table("user_tokens").update({
        "access_token": encrypt_token(tokens["access_token"]),
        "expires_at": tokens.get("expires_in")
    }).eq("email", email).execute()
    return tokens["access_token"]

# ---------- Google OAuth ----------
oauth = OAuth()
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/calendar.readonly "
            "https://www.googleapis.com/auth/drive.readonly"
        ),
        "access_type": "offline",
        "prompt": "consent"
    },
)

# ---------- Routes ----------
@auth_bp.route("/login")
def login():
    redirect_uri = url_for("auth.callback", _external=True)
    print(f"Session before redirect: {session}")
    return google.authorize_redirect(
        redirect_uri,
        prompt="consent",
        access_type="offline"
    )
    

# @auth_bp.route("/logout")
# def logout():
#     session.pop("user", None)
#     session.pop("token", None)
#     return jsonify({"message": "Logged out successfully"})
@auth_bp.route("/logout")
def logout():
    # Clear Google session
    session.pop("user", None)
    session.pop("token", None)
    
    # Clear GitHub session
    session.pop("github_user", None)
    session.pop("github_oauth_token", None)
    
    # Clear everything just in case
    session.clear()

    resp = jsonify({"message": "Logged out successfully"})
    resp.set_cookie("session", "", expires=0, path="/")
    return resp

@auth_bp.route("/auth/callback")
def callback():
    print(f"Session on callback: {session}")
    token = google.authorize_access_token()
    if not token:
        return jsonify({"error": "Failed to fetch token"}), 400

    # Fetch user info
    user_info = google.get("https://openidconnect.googleapis.com/v1/userinfo").json()
    email = user_info.get("email")

    # Save tokens to Supabase
    upsert_data = {
        "email": email,
        "access_token": encrypt_token(token["access_token"]),
        "expires_at": token.get("expires_at")
    }
    if token.get("refresh_token"):
        upsert_data["refresh_token"] = encrypt_token(token["refresh_token"])
    supabase_table("user_tokens").upsert(upsert_data, on_conflict="email").execute()

    # ✅ Create proper Google credentials and store in Flask session
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/keep",
            "openid", "email", "profile"
        ]
    )

    # ✅ Store user + creds in session for your agent
    session["user"] = {
        "email": email,
        "name": user_info.get("name"),
        "picture": user_info.get("picture")
    }
    session["token"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes)
    }

    print("✅ User logged in:", email)
    print("✅ Session after login:", dict(session))
    print("✅ Logged in user scopes:", creds.scopes)

    # Redirect back to React frontend
    return redirect("https://ai-agent-0qhy.onrender.com/ask")

# ---------- Protected route: /me ----------
@auth_bp.route("/me")
def get_user_profile():
    # Check Google session
    google_user = session.get("user")
    # Check GitHub session
    github_user = session.get("github_user")
    if google_user:
        return jsonify({"provider": "google", "user": google_user})
    elif github_user:
        return jsonify({"provider": "github", "user": github_user})
    else:
        return jsonify({"error": "User not logged in"}), 401