# app.py
from flask import Flask, jsonify, request, session, send_file, send_from_directory
import traceback
from flask_cors import CORS
from dotenv import load_dotenv
import os
import pytz
from datetime import datetime, timezone, timedelta
import base64
from email.mime.text import MIMEText

# Google OAuth & APIs
from auth import auth_bp, oauth
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# GitHub OAuth
from github_auth import github_auth_bp
from flask_dance.contrib.github import github

# Whisper & TTS
import whisper
from gtts import gTTS

# LangChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# PDF
from PyPDF2 import PdfReader

# -------------------- Setup --------------------
load_dotenv()
app = Flask(
    __name__,
    static_folder="frontend/build/static",
    static_url_path="/static"
)
app.secret_key = os.getenv("SESSION_SECRET")
CORS(app, origins=["https://ai-agent-0qhy.onrender.com"], supports_credentials=True)

app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(github_auth_bp)
oauth.init_app(app)

import os
os.environ["PATH"] += os.pathsep + r"D:\AI Research CoPilot\ffmpeg\bin"

# -------------------- Models --------------------
stt_model = None  

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
    api_key=os.getenv("GOOGLE_API_KEY")
)

# -------------------- Helpers --------------------
def get_google_creds():
    token_data = session.get("token")
    if not token_data:
        raise Exception("User not authenticated via Google")
    return Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

# -------------------- PDF Tools --------------------
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from flask import url_for
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def read_pdf(file_path: str = None):
    """Reads PDF text from uploads folder or latest uploaded file."""
    try:
        if not file_path:
            file_path = session.get("current_pdf")
            if not file_path:
                return "❌ No PDF uploaded yet."
        safe_name = (file_path)
        full_path = os.path.join(UPLOAD_FOLDER, safe_name)
        if not os.path.exists(full_path):
            return "❌ PDF not found on server."
        reader = PdfReader(full_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        text = "\n".join(text_parts).strip()
        return text or "⚠️ PDF contains no extractable text."
    except Exception as e:
        print("❌ read_pdf ERROR:", traceback.format_exc())
        return f"Error reading PDF: {str(e)}"


def summarize_pdf(filename: str = None):
    """Summarizes the latest uploaded PDF file."""
    try:
        # Use latest uploaded PDF if filename not provided
        if not filename:
            filename = session.get("current_pdf")
            if not filename:
                return "❌ No PDF uploaded yet."

        text = read_pdf(filename)
        if not text or text.startswith(("❌", "Error")):
            return text

        # Clear memory to avoid using old PDF context
        memory.clear()

        prompt = PromptTemplate(
            template="Summarize the following PDF content concisely:\n\n{text}",
            input_variables=["text"]
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run({"text": text})
    except Exception as e:
        return f"Error summarizing PDF: {e}"

pdf_reader_tool = Tool(
    name="PDFReader",
    func=read_pdf,
    description="Reads text from the latest uploaded PDF file."
)

pdf_summarizer_tool = Tool(
    name="PDFSummarizer",
    func=summarize_pdf,
    description="Summarizes the latest uploaded PDF file."
)

# -------------------- Gmail --------------------
import json

def parse_email_request(user_input: str):
    """
    Uses Gemini to extract email details from a natural prompt.
    Example: "Send a mail to xyz@gmail.com to apply for leave"
    """
    try:
        parse_prompt = f"""
        You are an AI email parser. Extract details to send an email from this text:
        "{user_input}"

        Return JSON with keys:
        {{
          "to": "receiver email address",
          "subject": "a short relevant subject line",
          "body": "a formal, polite email body"
        }}
        """

        parser_chain = LLMChain(llm=llm, prompt=PromptTemplate(
            template=parse_prompt, input_variables=[]
        ))

        response = parser_chain.run()
        print("🧠 Raw email parse:", response)

        # Extract JSON safely
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != -1:
            data = json.loads(response[start:end])
        else:
            raise ValueError("Invalid JSON format from AI")

        if not data.get("to") or "@" not in data["to"]:
            raise ValueError("Invalid or missing email address")
        return data

    except Exception as e:
        print("❌ parse_email_request ERROR:", traceback.format_exc())
        return None

def read_emails(_input=None):
    creds = get_google_creds()
    service = build("gmail", "v1", credentials=creds)
    messages = service.users().messages().list(userId="me", maxResults=5).execute().get("messages", [])
    snippets = []
    for msg in messages:
        data = service.users().messages().get(userId="me", id=msg["id"]).execute()
        snippets.append(data.get("snippet", ""))
    return "\n\n".join(snippets) if snippets else "No recent emails."

def send_email(input_text: str):
    """
    Smart email sender — can understand natural prompts or structured input.
    Example:
      - "send a mail to xyz@gmail.com for 2 days leave"
      - "to=xyz@gmail.com, subject=Hello, body=How are you?"
    """
    try:
        creds = get_google_creds()
        service = build("gmail", "v1", credentials=creds)

        # Try to detect JSON-style or natural language
        if "to=" in input_text and "subject=" in input_text and "body=" in input_text:
            parts = dict(p.split("=", 1) for p in input_text.split(",") if "=" in p)
            to = parts.get("to")
            subject = parts.get("subject", "No Subject")
            body = parts.get("body", "")
        else:
            parsed = parse_email_request(input_text)
            if not parsed:
                return "❌ Could not understand email request."
            to, subject, body = parsed["to"], parsed["subject"], parsed["body"]

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return f"✅ Email sent successfully to {to}"

    except Exception as e:
        print("❌ send_email ERROR:", traceback.format_exc())
        return f"Failed to send email: {str(e)}"


# -------------------- Calendar --------------------
def list_calendar_events(_input=None, max_events=5):
    creds = get_google_creds()
    service = build("calendar", "v3", credentials=creds)
    calendar = service.calendars().get(calendarId="primary").execute()
    tz_name = calendar.get("timeZone", "UTC")
    local_tz = pytz.timezone(tz_name)
    now_utc = datetime.now(timezone.utc)
    time_min = now_utc.isoformat()
    time_max = (now_utc + timedelta(days=30)).isoformat()
    today = datetime.now(local_tz).strftime("%A, %B %d, %Y")

    calendar_list = service.calendarList().list().execute()
    all_events = []

    for cal_entry in calendar_list.get("items", []):
        events = service.events().list(
            calendarId=cal_entry["id"],
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])
        for event in events:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            if "dateTime" in event["start"]:
                start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(local_tz)
                start_str = start_dt.strftime("%A, %B %d, %Y %I:%M %p")
            else:
                start_str = start_raw
            all_events.append(f"{start_str} - {event.get('summary','No Title')}")

    if not all_events:
        return f"Today is {today}.\nNo upcoming events found."
    all_events.sort()
    return f"Today is {today}.\nUpcoming events:\n" + "\n".join(all_events[:max_events])

# -------------------- Google Docs Tools --------------------
def get_docs_service():
    creds = get_google_creds()
    return build("docs", "v1", credentials=creds)

def get_drive_service():
    creds = get_google_creds()
    return build("drive", "v3", credentials=creds)

def list_docs(_input=None):
    try:
        drive_service = get_drive_service()
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=5, fields="files(id, name)"
        ).execute()
        docs = results.get("files", [])
        if not docs:
            return "No Google Docs found."
        return "\n".join([f"{d['name']} - {d['id']}" for d in docs])
    except Exception as e:
        return f"Error listing docs: {str(e)}"

def create_doc(input_text: str):
    try:
        parts = dict(p.split("=", 1) for p in input_text.split(",") if "=" in p)
        title, content = parts.get("title", "Untitled"), parts.get("content", "")
        docs_service = get_docs_service()
        drive_service = get_drive_service()
        new_doc = drive_service.files().create(
            body={"name": title, "mimeType": "application/vnd.google-apps.document"}
        ).execute()
        doc_id = new_doc.get("id")
        if content:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]}
            ).execute()
        return f"✅ Created Google Doc: {title} ({doc_id})"
    except Exception as e:
        return f"Error creating doc: {str(e)}"

def read_doc(input_text: str):
    try:
        doc_id = input_text.split("=", 1)[1].strip()
        docs_service = get_docs_service()
        doc = docs_service.documents().get(documentId=doc_id).execute()
        content = ""
        for elem in doc.get("body", {}).get("content", []):
            text = elem.get("paragraph", {}).get("elements", [{}])[0].get("textRun", {}).get("content", "")
            content += text
        return f"📖 {doc.get('title')}:\n\n{content.strip()}"
    except Exception as e:
        return f"Error reading doc: {str(e)}"

# -------------------- GitHub Tools --------------------
def list_github_repos(_input=None):
    if not github.authorized or not session.get("github_user"):
        return "⚠️ Please log in with GitHub first."
    resp = github.get("/user/repos")
    if not resp.ok:
        return f"❌ Failed: {resp.text}"
    return "\n".join([r["name"] for r in resp.json()]) or "No repos found."

# -------------------- LangChain Agent --------------------
search_tool = DuckDuckGoSearchRun()
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

tools = [
    search_tool,
    Tool(name="GmailReader", func=read_emails, description="Reads last 5 Gmail messages."),
    Tool(name="GmailSender", func=send_email, description="Send email. Format: to=<>, subject=<>, body=<>."),
    Tool(name="CalendarViewer", func=list_calendar_events, description="Shows Google Calendar events."),
    Tool(name="DocsList", func=list_docs, description="List Google Docs."),
    Tool(name="DocsCreate", func=create_doc, description="Create Google Doc. Format: title=<>, content=<>."),
    Tool(name="DocsRead", func=read_doc, description="Read Google Doc. Format: id=<doc_id>."),
    Tool(name="GitHubRepos", func=list_github_repos, description="List GitHub repos."),
    pdf_reader_tool,
    pdf_summarizer_tool
]

react_prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=False, handle_parsing_errors=True)

# -------------------- Routes --------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Accepts either:
      - multipart form with key "files" (multiple) or key "file" (single)
      - returns JSON with saved filenames and preview URLs
    """
    try:
        uploaded = []
        # support both 'files' (multiple) and 'file' (single)
        if "files" in request.files:
            files = request.files.getlist("files")
        elif "file" in request.files:
            files = [request.files.get("file")]
        else:
            return jsonify({"error": "No files uploaded (expected form key 'files' or 'file')"}), 400

        if not files:
            return jsonify({"error": "No files found in request"}), 400

        saved_files = []
        for f in files:
            if not f or f.filename == "":
                continue
            filename = (f.filename)
            if not allowed_file(filename):
                return jsonify({"error": f"File type not allowed: {filename}"}), 400
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            # if same filename exists, you may add a suffix to avoid clobbering:
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                counter += 1
            f.save(save_path)
            saved_files.append(filename)

        if not saved_files:
            return jsonify({"error": "No valid files saved"}), 400

        # store in session
        session["uploaded_files"] = saved_files
        session["current_pdf"] = saved_files[-1]  # track latest uploaded file

        # build preview URLs (served from /uploads/<filename>)
        previews = [url_for("serve_upload", filename=n, _external=False) for n in saved_files]

        return jsonify({
            "message": f"{len(saved_files)} file(s) uploaded successfully",
            "files": saved_files,
            "previews": previews
        }), 200

    except Exception as e:
        print("❌ upload_files ERROR:", traceback.format_exc())
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    # Serves uploaded files so frontend can preview them via <img> or embed PDF
    try:
        safe = (filename)
        return send_from_directory(UPLOAD_FOLDER, safe, as_attachment=False)
    except Exception as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404
    
# -------------------- STT Route --------------------
def get_stt_model():
    global stt_model
    if stt_model is None:
        print("🔊 Loading Whisper Tiny model on demand...")
        stt_model = whisper.load_model("tiny", device="cpu")
        torch.set_grad_enabled(False)
    return stt_model

@app.route("/stt", methods=["POST"])
def stt():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file received"}), 400

        audio_file = request.files["audio"]
        temp_path = os.path.join(UPLOAD_FOLDER, "temp_audio.wav")
        audio_file.save(temp_path)

        model = get_stt_model()  # <-- Lazy load happens here
        print("🎙️ Transcribing with Whisper...")
        result = model.transcribe(temp_path)
        text = result.get("text", "").strip()
        print(f"✅ Transcribed text: {text}")

        os.remove(temp_path)
        return jsonify({"text": text})
    except Exception as e:
        print("❌ Error in /stt:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500



# -------------------- TTS Route --------------------
@app.route("/tts", methods=["POST"])
def tts():
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400

        temp_path = os.path.join(UPLOAD_FOLDER, "temp_tts.mp3")
        tts = gTTS(text=text, lang="en")
        tts.save(temp_path)

        return send_file(temp_path, mimetype="audio/mpeg")
    except Exception as e:
        print("❌ Error in /tts:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "No query provided"}), 400

        user = session.get("user") or session.get("github_user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        # 🧠 Detect PDF summarization
        if "PDF" in query.upper() and "SUMMARIZE" in query.upper():
            filename = session.get("current_pdf")
            output = summarize_pdf(filename)
            return jsonify({"answer": output}), 200

        # 🤖 Normal agent query
        result = agent_executor.invoke({"input": query})

        # ✅ Always extract clean text output
        if isinstance(result, dict):
            output = result.get("output") or result.get("answer") or str(result)
        else:
            output = str(result)

        return jsonify({"answer": output}), 200

    except Exception as e:
        import traceback
        print("❌ /ask ERROR:\n", traceback.format_exc())
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/me")
def get_me():
    user_data = {}
    if "user" in session:
        user_data["user"] = session["user"]
    if "github_user" in session:
        user_data["github_user"] = session["github_user"]
    if not user_data:
        return jsonify({"error": "No user logged in"}), 401
    return jsonify(user_data)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
    file_path = os.path.join(build_dir, path)
    
    if path != "" and os.path.exists(file_path):
        return send_from_directory(build_dir, path)
    else:
        return send_from_directory(build_dir, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)