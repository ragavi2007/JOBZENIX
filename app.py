from flask import Flask, render_template, request, jsonify
import fitz
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# ENV LOAD
# -----------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# -----------------------------
# MONGO CONNECTION
# -----------------------------
client = None
db = None
users = None

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")

    print("✅ MongoDB Connected Successfully!")

    db = client["careertutor"]
    users = db["users"]
    active_users = db["active_users"]

except Exception as e:
    print("❌ MongoDB Connection Failed:", e)
    users = None

# -----------------------------
# PAGES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/admin-login")
def admin_login():
    return render_template("admin-login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/resumebuilder")
def resumebuilder():
    return render_template("resumebuilder.html")


@app.route("/atschecker")
def atschecker():
    return render_template("atschecker.html")


@app.route("/mockinterview")
def mockinterview():
    return render_template("mockinterview.html")


@app.route("/certificateverifier")
def certificateverifier():
    return render_template("certificateverifier.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/signout")
def signout():
    return render_template("signout.html")



@app.route("/skillgapanalyzer")
def skillgapanalyzer():
    return render_template("skillgapanalyzer.html")
# -----------------------------
# REGISTER API (SAVE TO MONGO)
# -----------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json

    if users is None:
        return jsonify({"status": "error", "msg": "DB not connected"})

    # duplicate check
    if users.find_one({"email": data["email"]}):
        return jsonify({"status": "exists", "msg": "User already exists"})

    users.insert_one({
    "name": data["name"],
    "email": data["email"],
    "password": data["password"],
    "status": "Active"
})

    return jsonify({"status": "ok", "msg": "Registered successfully"})

# -----------------------------
# LOGIN API
# -----------------------------
@app.route("/api/login", methods=["POST"])
@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.json

    if users is None:
        return jsonify({
            "status": "error",
            "msg": "DB not connected"
        })

    user = users.find_one({
        "email": data["email"],
        "password": data["password"]
    })

    if not user:
        return jsonify({
            "status": "fail",
            "msg": "Invalid credentials"
        })

    # BLOCK CHECK
    if user.get("status") == "Blocked":
        return jsonify({
            "status": "fail",
            "msg": "Account Blocked By Admin"
        })

    active_users.insert_one({
        "name": user["name"],
        "email": user["email"],
        "login_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "status": user.get("status", "Active")
    })

    return jsonify({
        "status": "ok",
        "name": user["name"]
    })
@app.route("/api/admin/users")
def admin_users():

    data = list(
        active_users.find(
            {},
            {"_id": 0}
        )
    )

    return jsonify(data)

@app.route("/api/admin/toggle-user", methods=["POST"])
def toggle_user():

    data = request.json
    email = data.get("email")

    user = users.find_one({
        "email": email
    })

    if not user:
        return jsonify({
            "message": "User not found"
        })

    new_status = "Blocked"

    if user.get("status") == "Blocked":
        new_status = "Active"

    users.update_one(
        {"email": email},
        {
            "$set": {
                "status": new_status
            }
        }
    )

    active_users.update_many(
        {"email": email},
        {
            "$set": {
                "status": new_status
            }
        }
    )

    return jsonify({
        "message": f"User {new_status}"
    })

# -----------------------------
# PDF EXTRACT
# -----------------------------
def extract_pdf_text(pdf_file):
    text = ""
    pdf = fitz.open(stream=pdf_file.read(), filetype="pdf")

    for page in pdf:
        text += page.get_text()

    return text

# -----------------------------
# ATS ANALYZER
# -----------------------------
@app.route("/analyze", methods=["POST"])
def analyze():

    resume_file = request.files["resume"]
    jd_text = request.form.get("jd", "")

    if resume_file.filename.lower().endswith(".pdf"):
        resume_text = extract_pdf_text(resume_file)
    else:
        resume_text = resume_file.read().decode("utf-8", errors="ignore")

    resume_words = set(resume_text.lower().split())
    jd_words = set(jd_text.lower().split())

    matching_keywords = list(resume_words.intersection(jd_words))
    missing_keywords = list(jd_words - resume_words)

    total_jd_keywords = len(jd_words)

    job_match_pct = int(
        (len(matching_keywords) / total_jd_keywords) * 100
    ) if total_jd_keywords > 0 else 0

    ats_score = min(job_match_pct + 20, 100)

    if ats_score >= 80:
        verdict = "Excellent"
        verdict_color = "green"
    elif ats_score >= 60:
        verdict = "Needs Minor Improvements"
        verdict_color = "yellow"
    else:
        verdict = "Needs Major Improvements"
        verdict_color = "red"

    return jsonify({
        "atsScore": ats_score,
        "jobMatchPct": job_match_pct,
        "readabilityScore": 75,
        "industryRelevance": 80,
        "resumeLength": "1 Page",

        "verdict": verdict,
        "verdictColor": verdict_color,

        "matchingKeywords": matching_keywords[:10],
        "missingKeywords": missing_keywords[:10],

        "missingTechSkills": missing_keywords[:5],
        "missingSoftSkills": [],

        "strengths": [
            "Resume uploaded successfully",
            "Keywords matched with JD"
        ],

        "weaknesses": [
            "Some JD keywords are missing"
        ],

        "grammarIssues": [],

        "contactCheck": {
            "email": True,
            "phone": True,
            "linkedin": False,
            "github": False,
            "address": False,
            "portfolio": False
        },

        "sectionScores": {
            "skills": ats_score,
            "experience": ats_score,
            "education": 80,
            "projects": 70
        },

        "skillsGap": [
            {
                "name": keyword,
                "pct": 0
            }
            for keyword in missing_keywords[:5]
        ],

        "actionVerbImprovements": [
            {
                "old": "Worked",
                "new": "Developed",
                "context": "Projects"
            }
        ],

        "aiSuggestions": [
            "Add missing JD keywords",
            "Add more measurable achievements",
            "Include certifications"
        ]
    })

# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)