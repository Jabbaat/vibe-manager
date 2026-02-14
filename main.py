from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from typing import Optional
import os
import re
import io
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from docx import Document
from google import genai
from google.genai import types
from google.cloud import firestore
from datetime import datetime

# App definitie
app = FastAPI(title="Eddiecool Agent V9 (Daily Briefing Edition)")

# --- CONFIGURATIE ---
TEMP_DIR = "/tmp"
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") 
SESSION_ID = "eddie_session_v1" 
ADMIN_PASSWORD = os.environ.get("VIBE_PASSWORD", "eddie")
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Mail Configuratie
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "")

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# DB Connectie
try:
    db = firestore.Client(project=PROJECT_ID)
    print(f"✅ Verbonden met Firestore: {PROJECT_ID}")
except Exception as e:
    print(f"⚠️ Geen DB (lokaal?): {e}")
    db = None

# --- HET BREIN (V8 + BRIEFING) ---
SYSTEM_INSTRUCTION = """
JIJ BENT: De Eddiecool Vibe_Agent.
KENMERKEN:
1. Nederlands, Neobrutalist, Direct en enthousiast.
2. Je bent een ONDERZOEKER. Gebruik Google Search voor AI nieuws en crypto feiten.
3. Je kunt bestanden (PDF, DOCX, Afbeeldingen) LEZEN en ANALYSEREN.
4. Je hebt een olifantengeheugen.

BELANGRIJK:
- Houd antwoorden in de chat beknopt en 'punchy'.
- Gebruik Markdown.
"""

# --- HELPERS: DATABASE & FILES ---
def save_message(role, text):
    if not db: return
    try:
        doc_ref = db.collection("chats").document(SESSION_ID).collection("messages").document()
        doc_ref.set({"role": role, "content": str(text)[:10000], "timestamp": datetime.now()})
    except: pass

def get_history():
    if not db: return []
    try:
        docs = db.collection("chats").document(SESSION_ID).collection("messages") \
                 .order_by("timestamp", direction=firestore.Query.ASCENDING).limit_to_last(15).get()
        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append(types.Content(role=data["role"], parts=[types.Part(text=str(data["content"]))]))
        return history
    except: return []

def read_doc_file(file_bytes, filename):
    try:
        if filename.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_bytes))
            return df.to_markdown(index=False)
        else: return file_bytes.decode("utf-8")
    except Exception as e: return f"Fout: {str(e)}"

# --- HELPERS: NOTIFICATIES (NIEUW!) ---
def stuur_email(onderwerp, html_tekst):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return "Geen mailgegevens ingesteld in Google Cloud."

    msg = MIMEText(html_tekst, 'html')
    msg['Subject'] = onderwerp
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        return "✅ Mail verzonden!"
    except Exception as e:
        return f"❌ Mail Fout: {e}"

def get_bitcoin_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur", timeout=5)
        return f"€ {r.json()['bitcoin']['eur']:,.0f}".replace(",", ".")
    except:
        return "Prijs tijdelijk onbekend"

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
def home(): 
    return html_content

# --- DE AUTO-PILOT ROUTE (NIEUW!) ---
@app.get("/cron/daily_news")
def trigger_daily_news(token: str = ""):
    """Dit is de onzichtbare knop die de Cloud Scheduler elke ochtend indrukt."""
    # Simpele beveiliging: de token in de URL moet gelijk zijn aan je wachtwoord
    if token != ADMIN_PASSWORD:
        return {"error": "Toegang geweigerd. Verkeerde token."}
        
    try:
        btc_prijs = get_bitcoin_price()
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        Maak een vette, Neobrutalistische dagelijkse briefing. 
        Zoek met Google Search naar de 3 belangrijkste nieuwtjes over AI van de afgelopen 24 uur.
        De huidige Bitcoin prijs is: {btc_prijs}.
        
        Format het als een mooie HTML email:
        Gebruik <h2>, <ul>, <li>, <b> en <br>.
        Maak het enthousiast, direct en to the point!
        Begin de email met een knallende begroeting voor Eddie en de huidige BTC prijs.
        """
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        nieuws_html = response.text
        
        # Stuur de mail!
        status = stuur_email("🚀 Jouw Dagelijkse AI & Crypto Briefing", nieuws_html)
        
        return {"status": status, "preview": "Briefing is gegenereerd en het mail-commando is uitgevoerd."}
    except Exception as e:
        return {"error": str(e)}

# --- CHAT ROUTE (ON-DEMAND) ---
@app.post("/chat_with_file")
async def chat_with_file(text: str = Form(...), password: str = Form(...), file: Optional[UploadFile] = File(None)):
    if password != ADMIN_PASSWORD:
        return {"response": "⛔ FOUT WACHTWOORD!", "raw_text": "Fout wachtwoord."}

    try:
        client = genai.Client(api_key=API_KEY)
        db_history = get_history()
        current_parts = [types.Part(text=text)]
        
        file_msg = ""
        if file:
            file_bytes = await file.read()
            mime = file.content_type
            file_msg = f" [Bestand: {file.filename}]"
            if mime.startswith("image/") or mime == "application/pdf":
                current_parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))
            else:
                txt = read_doc_file(file_bytes, file.filename)
                current_parts.append(types.Part(text=f"--- BESTAND {file.filename} ---\n{txt}"))

        save_message("user", text + file_msg)
        full_contents = db_history + [types.Content(role="user", parts=current_parts)]

        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=full_contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        final = response.text
        html = final.replace("\n", "<br>").replace("**", "<b>").replace("eind**", "eind</b>")
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
        
        save_message("model", final)
        return {"response": html, "raw_text": final}

    except Exception as e:
        return {"response": f"🔥 Fout: {str(e)}", "raw_text": "Error."}

# --- INTERFACE (UI) ---
html_content = r"""
<!DOCTYPE html>
<html>
<head>
    <title>Eddiecool Vibe Agent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        :root { --acid: #ccff00; --pink: #ff90e8; --black: #000; --white: #fff; }
        body { background: var(--pink); font-family: 'Courier New', monospace; margin: 0; height: 100dvh; display: flex; justify-content: center; align-items: center; }
        .layout { width: 100%; max-width: 900px; height: 95vh; background: var(--white); border: 6px solid var(--black); box-shadow: 12px 12px 0 var(--black); display: flex; flex-direction: column; position: relative; }
        .header { background: var(--acid); border-bottom: 6px solid var(--black); padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        h1 { margin: 0; font-size: 1.2rem; font-weight: 900; }
        .chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .msg { padding: 10px 15px; max-width: 85%; border: 4px solid var(--black); font-weight: 700; word-wrap: break-word; }
        .model { align-self: flex-start; background: var(--acid); box-shadow: 6px 6px 0 var(--black); }
        .user { align-self: flex-end; background: var(--black); color: var(--white); }
        .controls { padding: 15px; background: var(--pink); border-top: 6px solid var(--black); display: flex; gap: 10px; align-items: stretch; }
        input[type="text"] { flex: 1; padding: 10px; border: 4px solid var(--black); font-weight: 700; min-width: 0; }
        button, .file-label { background: var(--black); color: var(--white); border: 4px solid var(--black); font-weight: 900; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .file-label { padding: 0 15px; font-size: 1.5rem; background: var(--white); color: black; box-shadow: 4px 4px 0 var(--black); }
        input[type="file"] { display: none; }
        .mic-btn { width: 50px; font-size: 1.5rem; background: var(--white); color: black; box-shadow: 4px 4px 0 var(--black); }
        .mic-btn.listening { background: red; color: white; animation: pulse 1s infinite; }
        .send-btn { padding: 0 20px; font-size: 1rem; }
        button:active, .file-label:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--black); }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        #loginOverlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: var(--pink); z-index: 1000; display: flex; justify-content: center; align-items: center; }
        .login-box { background: white; border: 6px solid black; padding: 30px; box-shadow: 10px 10px 0 black; text-align: center; }
    </style>
</head>
<body>
    <div id="loginOverlay">
        <div class="login-box">
            <h1>🔒 SECURITY CHECK</h1>
            <input type="password" id="passInput" placeholder="Wachtwoord..." style="width: 100%; padding: 10px; margin-bottom: 10px; border: 4px solid black;">
            <button onclick="checkLogin()" style="width: 100%; padding: 10px;">UNLOCK</button>
        </div>
    </div>
    <div class="layout">
        <div class="header">
            <h1>Daily Briefing Agent</h1>
            <div id="voiceToggle" onclick="toggleVoice()" style="cursor:pointer; font-weight:bold;">🔊 AAN</div>
        </div>
        <div class="chat" id="chat">
            <div class="msg model">SYSTEM ONLINE. 🔓<br>Mijn nieuws-radar staat aan. Wil je de Crypto & AI update nu in de chat, of zal ik hem mailen? 🚀</div>
        </div>
        <div class="controls">
            <label class="file-label">📎 <input type="file" id="fileInput"></label>
            <button class="mic-btn" id="micBtn" onclick="startDictation()">🎤</button>
            <input type="text" id="in" placeholder="Typ of upload..." onkeypress="if(event.key==='Enter') send()">
            <button class="send-btn" onclick="send()">GO</button>
        </div>
    </div>
    <script>
        let userPassword = localStorage.getItem("vibe_password") || "";
        let voiceEnabled = true; let synthesis = window.speechSynthesis;
        if(userPassword) document.getElementById("passInput").value = userPassword;
        function checkLogin() {
            let p = document.getElementById("passInput").value;
            if(p) { userPassword = p; localStorage.setItem("vibe_password", p); document.getElementById("loginOverlay").style.display = "none"; } else alert("Vul een wachtwoord in!");
        }
        function toggleVoice() {
            voiceEnabled = !voiceEnabled; document.getElementById("voiceToggle").innerText = voiceEnabled ? "🔊 AAN" : "🔇 UIT"; if(!voiceEnabled) synthesis.cancel();
        }
        function startDictation() {
            if (window.hasOwnProperty('webkitSpeechRecognition')) {
                var recognition = new webkitSpeechRecognition(); let micBtn = document.getElementById("micBtn");
                recognition.continuous = false; recognition.interimResults = false; recognition.lang = "nl-NL";
                recognition.onstart = function() { micBtn.classList.add("listening"); };
                recognition.onresult = function(e) { document.getElementById('in').value = e.results[0][0].transcript; recognition.stop(); micBtn.classList.remove("listening"); };
                recognition.onend = function() { micBtn.classList.remove("listening"); };
                recognition.start();
            } else alert("Gebruik Chrome voor spraak.");
        }
        async function send() {
            let i = document.getElementById("in"); let f = document.getElementById("fileInput"); let t = i.value.trim(); let file = f.files[0];
            if(!t && !file) return;
            let c = document.getElementById("chat");
            c.innerHTML += `<div class="msg user">${t + (file ? `<br><small>📎 ${file.name}</small>` : "")}</div>`; i.value = ""; synthesis.cancel();
            const fd = new FormData(); fd.append("text", t); fd.append("password", userPassword); if(file) fd.append("file", file);
            try {
                let r = await fetch("/chat_with_file", { method: "POST", body: fd }); let d = await r.json();
                if(d.response && d.response.includes("FOUT WACHTWOORD")) {
                     c.innerHTML += `<div class="msg model" style="background:red; color:white;">⛔ FOUT WACHTWOORD!</div>`; localStorage.removeItem("vibe_password"); setTimeout(() => location.reload(), 2000);
                } else {
                    c.innerHTML += `<div class="msg model">${d.response}</div>`;
                    if(voiceEnabled && d.raw_text) { let u = new SpeechSynthesisUtterance(d.raw_text.replace(/<[^>]*>/g, "")); u.lang = 'nl-NL'; synthesis.speak(u); }
                }
            } catch(e) { c.innerHTML += `<div class="msg model">ERROR: ${e}</div>`; }
            c.scrollTop = c.scrollHeight; f.value = "";
        }
    </script>
</body>
</html>
"""
