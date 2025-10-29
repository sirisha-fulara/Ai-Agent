# github_auth.py
from flask import Blueprint, redirect, url_for, jsonify, session, request
from flask_dance.contrib.github import make_github_blueprint, github
import os

# Flask-Dance blueprint (callback route: /github/authorized)
github_auth_bp = make_github_blueprint(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    scope="read:user,repo,user:email",
    # redirect_to="github.github_callback",  # <-- redirect here after OAuth
    redirect_url="/github/callback"
)

# Ensure GitHub API returns JSON
github_auth_bp.session.headers.update({"Accept": "application/json"})

# -------------------- Routes --------------------

# Force GitHub OAuth login every time
@github_auth_bp.route("/login/github")
def github_login():
    # Always redirect to Flask-Dance GitHub login
    return redirect(url_for("github.login"))

# Handle redirect after OAuth completes
@github_auth_bp.route("/github/callback")
def github_callback():
    if not github.authorized:
        return redirect(url_for("github.login"))
    
    resp = github.get("/user")
    if not resp.ok:
        return jsonify({"error": "Failed to fetch GitHub user info"}), 500

    # Save user info in session
    session["github_user"] = resp.json()

    # Determine frontend redirect (local vs production)
    frontend_url = os.environ.get("FRONTEND_URL", "https://ai-agent-0qhy.onrender.com")
    return redirect(f"{frontend_url}/ask")

# Fetch logged-in GitHub user
@github_auth_bp.route("/me")
def github_me():
    user = session.get("github_user")
    if not user:
        return jsonify({"error": "GitHub user not logged in"}), 401
    return jsonify(user)

# Fetch user repositories
@github_auth_bp.route("/repos")
def github_repos():
    if not github.authorized:
        return redirect(url_for("github.login"))

    resp = github.get("/user/repos")
    if not resp.ok:
        return jsonify({"error": "Failed to fetch repos"}), 500

    repos = [r["name"] for r in resp.json()]
    return jsonify({"repositories": repos})

# Create a GitHub issue
@github_auth_bp.route("/issue", methods=["POST"])
def github_issue():
    if not github.authorized:
        return redirect(url_for("github.login"))

    data = request.get_json()
    repo = data.get("repo")
    title = data.get("title")
    body = data.get("body", "")

    username = session.get("github_user", {}).get("login")
    if not username:
        return jsonify({"error": "GitHub user not logged in"}), 401

    resp = github.post(
        f"/repos/{username}/{repo}/issues",
        json={"title": title, "body": body}
    )
    if not resp.ok:
        return jsonify({"error": "Failed to create issue"}), 500

    return jsonify(resp.json())