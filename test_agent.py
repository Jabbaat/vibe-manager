from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import json
import re
import time
import pandas as pd
from docx import Document
from google import genai
from google.genai import types
from google.cloud import firestore
from datetime import datetime

app = FastAPI(title="De Eddiecool Vibe_Agent")

# --- CONFIGURATIE ---
TEMP_DIR = "/tmp"
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") 
SESSION_ID = "eddie_session_v1" 

# Start de Database verbinding
try:
    db = firestore.Client(project=PROJECT_ID)
    print(f"✅ Verbonden met Firestore Database: {PROJECT_ID}")
except Exception as e:
    print(f"⚠️ Kon niet verbinden met DB (lokaal?): {e}")
    db = None

# --- HET BREIN ---
SYSTEM_INSTRUCTION = """
JIJ BENT: De Eddiecool Vibe_Agent.
JE KENMERKEN:
1. Je spreekt Nederlands.
2. Je bent enthousiast, direct en creatief.
3. Je antwoorden worden mogelijk hardop voorgelezen. Houd zinnen liever kort en krachtig.
4. Je onthoudt alles (Database).
5. Je kunt bestanden maken (Creator Mode) en lezen (Vision).

BELANGRIJK:
- Gebruik [[FILE: naam]] ... [[ENDFILE]] voor bestanden.
"""

# --- HULP FUNCTIES (BACKEND) ---
def save_message(role, text):
    if not db: return
    doc_ref = db.collection("chats").document(SESSION_ID).collection("messages").document()
    doc_ref.set({"role": role, "content": text, "timestamp": datetime.now()})

def get_history():
    if not db: return []
    docs = db.collection("chats").document(SESSION_ID).collection("messages") \
             .order_by("timestamp", direction=firestore.Query.ASCENDING).limit_to_last(20).get()
    history = []
    for doc in docs:
        data = doc.to_dict()
        history.append(types.Content(role=data["role"], parts=[types.Part(text=data["content"])]))
    return history

def extract_and_save_files(text):
    pattern = r"\[\[FILE:\s*(.*?)\]\](.*?)\[\[ENDFILE\]\]"
    matches = re.findall(pattern, text, re.DOTALL)
    processed_text = text
    for filename, content in matches:
        filename = filename.strip()
        filepath = os.path.join(TEMP_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f: f.write(content.strip())  
        download_html = f"""<div class='download-box'><span class='file-icon'>💾</span>
            <div class='file-info'><strong>{filename}</strong><br>KLAAR OM TE DOWNLOADEN</div>
            <a href='/download/{filename}' target='_blank' class='download-btn'>DOWNLOAD</a></div>"""
        processed_text = re.sub(pattern, "", processed_text, flags=re.DOTALL)
        processed_text += download_html
    return processed_text

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

# --- API ENDPOINTS ---
@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path): return FileResponse(file_path, filename=filename)
    return {"error": "Bestand niet gevonden"}

@app.post("/chat_with_file")
async def chat_with_file(text: str = Form(...), file: Optional[UploadFile] = File(None)):
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        db_history = get_history()
        
        current_parts = []
        if text: current_parts.append(types.Part(text=text))
        
        file_msg = ""
        if file:
            file_bytes = await file.read()
            mime = file.content_type
            file_msg = f" [Bestand: {file.filename}]"
            if mime.startswith("image/") or mime == "application/pdf":
                current_parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))
            else:
                extracted_text = read_doc_file(file_bytes, file.filename)
                current_parts.append(types.Part(text=f"--- INHOUD {file.filename} ---\n{extracted_text}"))

        if not current_parts: return {"response": "..."}

        save_message("user", text + file_msg)
        full_contents = db_history + [types.Content(role="user", parts=current_parts)]

        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=full_contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        final_html = extract_and_save_files(response.text)
        save_message("model", response.text)
        
        return {"response": final_html, "raw_text": response.text}

    except Exception as e:
        return {"response": f"Server Fout: {str(e)}", "raw_text": "Er is een fout opgetreden."}

# --- INTERFACE (NEOBRUTALISM EXTREME - MOBILE PERFECTED) ---
html_content = r"""
<!DOCTYPE html>
<html>
<head>
    <title>De Eddiecool Vibe_Agent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <style>
        /* --- EXTREME NEOBRUTALISM THEME --- */
        :root {
            --acid-green: #ccff00;
            --hot-pink: #ff90e8;
            --deep-black: #000000;
            --paper-white: #ffffff;
        }

        * { box-sizing: border-box; }
        
        body { 
            background-color: var(--hot-pink); 
            background-image: radial-gradient(var(--deep-black) 1px, transparent 1px);
            background-size: 20px 20px;
            font-family: 'Courier New', monospace; 
            margin: 0; 
            height: 100vh; /* Fallback */
            height: 100dvh; /* Dynamic Height voor mobiel */
            display: flex; 
            justify-content: center; 
            align-items: center; 
            overflow: hidden; 
        }

        .layout {
            width: 100%;
            max-width: 900px;
            height: 95vh;
            background: var(--paper-white);
            border: 6px solid var(--deep-black);
            box-shadow: 12px 12px 0px var(--deep-black);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }

        /* HEADER */
        .header {
            background: var(--acid-green);
            border-bottom: 6px solid var(--deep-black);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }

        h1 { 
            margin: 0; 
            font-size: 1.5rem; 
            font-weight: 900; 
            text-transform: uppercase; 
            letter-spacing: -1px;
            color: var(--deep-black);
        }

        .voice-toggle { 
            font-weight: 900; 
            background: var(--paper-white); 
            padding: 8px 12px; 
            border: 4px solid var(--deep-black); 
            cursor: pointer; 
            box-shadow: 4px 4px 0px var(--deep-black);
            font-size: 0.9rem;
        }
        .voice-toggle.active { background: var(--hot-pink); }

        /* CHAT AREA */
        .chat { 
            flex: 1; 
            overflow-y: auto; 
            padding: 20px; 
            background: var(--paper-white); 
            display: flex; 
            flex-direction: column; 
            gap: 20px; 
            min-height: 0; /* Belangrijk voor flexbox scroll */
        }

        .msg { 
            padding: 15px 20px; 
            max-width: 85%; 
            font-size: 1.1rem; 
            line-height: 1.5; 
            border: 4px solid var(--deep-black); 
            font-weight: 700; 
        }
        
        .model { align-self: flex-start; background: var(--acid-green); box-shadow: 8px 8px 0px var(--deep-black); }
        .user { align-self: flex-end; background: var(--deep-black); color: var(--paper-white); box-shadow: -8px 8px 0px rgba(0,0,0,0.5); }

        /* CONTROLS (DESKTOP) */
        .controls { 
            padding: 20px; 
            background: var(--hot-pink); 
            border-top: 6px solid var(--deep-black); 
            display: flex; 
            gap: 10px; 
            align-items: stretch; 
            flex-shrink: 0; /* Zorgt dat balk nooit verdwijnt */
        }

        input[type="text"] { 
            flex: 1; 
            padding: 15px; 
            font-family: 'Courier New', monospace;
            font-weight: 900; 
            font-size: 1.1rem; 
            border: 4px solid var(--deep-black); 
            outline: none;
            box-shadow: 4px 4px 0px rgba(0,0,0,0.2);
            min-width: 0; 
        }

        button, .file-label, .mic-btn { 
            background: var(--deep-black); 
            color: var(--paper-white); 
            border: 4px solid var(--deep-black); 
            font-weight: 900; 
            cursor: pointer; 
            box-shadow: 6px 6px 0px var(--paper-white); 
            display: flex; align-items: center; justify-content: center;
        }
        
        .file-label { padding: 0 15px; font-size: 1.5rem; background: var(--paper-white); color: black; }
        .mic-btn { width: 60px; font-size: 1.5rem; background: var(--paper-white); color: black; }
        .mic-btn.listening { background: red; color: white; animation: pulse 1s infinite; }
        .send-btn { padding: 0 25px; font-size: 1.1rem; }

        button:active, .file-label:active, .mic-btn:active { 
            transform: translate(4px, 4px); 
            box-shadow: 2px 2px 0px var(--paper-white); 
        }

        /* DOWNLOAD BOX */
        .download-box {
            background: var(--paper-white);
            border: 4px solid var(--deep-black);
            padding: 15px;
            margin-top: 10px;
            display: flex; align-items: center; gap: 15px;
        }
        .download-btn { background: var(--deep-black); color: white; text-decoration: none; padding: 10px; font-weight: 900; }

        /* --- MOBIEL SPECIFIEKE FIX --- */
        @media (max-width: 600px) {
            body { 
                padding: 0; 
                background: var(--hot-pink); 
            }
            .layout { 
                width: 100%; 
                height: 100%; 
                height: 100dvh; /* Forceer hoogte naar viewport */
                border: none; 
                box-shadow: none; 
                max-width: none; 
            }
            
            .header { padding: 10px; }
            h1 { font-size: 1.1rem; }
            .voice-toggle { padding: 5px; font-size: 0.8rem; }
            
            /* DIT ZORGT DAT ALLES OP 1 LIJN BLIJFT */
            .controls { 
                padding: 10px; 
                flex-wrap: nowrap; 
                gap: 5px;
                background: var(--hot-pink); /* Zeker weten dat het zichtbaar is */
            }
            
            /* Compacte knoppen */
            .file-label { 
                width: 44px; padding: 0; justify-content: center; font-size: 1.2rem; flex-shrink: 0; 
            }
            .mic-btn { 
                width: 44px; font-size: 1.2rem; flex-shrink: 0; 
            }
            .send-btn { 
                width: auto; padding: 0 15px; font-size: 1rem; flex-shrink: 0; 
            }
            
            /* Input vult de rest */
            input[type="text"] { 
                flex: 1; 
                min-width: 0; 
                margin: 0; 
                font-size: 16px; /* Voorkomt inzoomen op iPhone */
                padding: 10px;
            }
        }

        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
        input[type="file"] { display: none; }
    </style>
</head>
<body>
    <div class="layout">
        <div class="header">
            <h1>De Eddiecool Vibe_Agent</h1>
            <div class="voice-toggle active" id="voiceToggle" onclick="toggleVoice()">
                🔊 AAN
            </div>
        </div>
        
        <div class="chat" id="chat">
            <div class="msg model">
                <strong>HÉ EDDIE! 👋</strong><br>
                Alles staat aan: Ogen, Oren & Geheugen.<br>
                Wat gaan we doen vandaag? 🚀
            </div>
        </div>
        
        <div class="controls">
            <label class="file-label">📎 <input type="file" id="fileInput"></label>
            <button class="mic-btn" id="micBtn" onclick="startDictation()">🎤</button>
            <input type="text" id="in" placeholder="Typ of praat..." onkeypress="if(event.key==='Enter') send()">
            <button class="send-btn" onclick="send()">GO</button>
        </div>
    </div>

    <script>
        let voiceEnabled = true;
        let synthesis = window.speechSynthesis;

        function toggleVoice() {
            voiceEnabled = !voiceEnabled;
            let el = document.getElementById("voiceToggle");
            if(voiceEnabled) {
                el.innerText = "🔊 AAN";
                el.classList.add("active");
            } else {
                el.innerText = "🔇 UIT";
                el.classList.remove("active");
                synthesis.cancel();
            }
        }

        function startDictation() {
            if (window.hasOwnProperty('webkitSpeechRecognition')) {
                var recognition = new webkitSpeechRecognition();
                let micBtn = document.getElementById("micBtn");
                recognition.continuous = false; recognition.interimResults = false; recognition.lang = "nl-NL";

                recognition.onstart = function() { micBtn.classList.add("listening"); };
                recognition.onresult = function(e) {
                    document.getElementById('in').value = e.results[0][0].transcript;
                    recognition.stop(); micBtn.classList.remove("listening");
                };
                recognition.onerror = function(e) { recognition.stop(); micBtn.classList.remove("listening"); };
                recognition.onend = function() { micBtn.classList.remove("listening"); };
                recognition.start();
            } else { alert("Gebruik Chrome voor spraak."); }
        }

        function speak(text) {
            if(!voiceEnabled) return;
            let cleanText = text.replace(/```[\s\S]*?```/g, " [Code blok] ")
                                .replace(/\[\[FILE:.*?\]\][\s\S]*?\[\[ENDFILE\]\]/g, " [Bestand klaar] ")
                                .replace(/\*/g, "");
            let utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'nl-NL'; utterance.rate = 1.1;
            synthesis.speak(utterance);
        }

        async function send() {
            let i = document.getElementById("in");
            let f = document.getElementById("fileInput");
            let c = document.getElementById("chat");
            let t = i.value.trim(); 
            let file = f.files[0];

            if(!t && !file) return;
            synthesis.cancel();
            
            let displayHtml = t + (file ? `<br><small>📎 ${file.name}</small>` : "");
            c.innerHTML += `<div class="msg user">${displayHtml}</div>`;
            i.value = "";
            
            let loadId = "load" + Date.now();
            c.innerHTML += `<div class="msg model" id="${loadId}">... LOADING ...</div>`;
            c.scrollTop = c.scrollHeight;
            
            const formData = new FormData();
            formData.append("text", t);
            if (file) formData.append("file", file);

            try {
                let r = await fetch("/chat_with_file", { method: "POST", body: formData });
                let d = await r.json();
                document.getElementById(loadId).remove();
                
                let txt = d.response.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
                c.innerHTML += `<div class="msg model">${txt}</div>`;
                f.value = ""; 
                if(d.raw_text) speak(d.raw_text);
            } catch(e) { document.getElementById(loadId).innerText = "ERROR: " + e; }
            c.scrollTop = c.scrollHeight;
        }
    </script>
</body>
</html>
"""