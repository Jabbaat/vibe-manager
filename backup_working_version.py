from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import os
from google import genai
from google.genai import types

app = FastAPI(title="Vibe Manager - Neobrutalism")

# --- INSTRUCTIE ---
SYSTEM_INSTRUCTION = """
JIJ BENT: De Vibe Manager van EddieCool.
JE TAAK: Genereer creatieve content, maar gebruik FEITEN als daarom gevraagd wordt.
BELANGRIJK: Gebruik de Google Search tool als de gebruiker vraagt om actuele informatie (nieuws, prijzen, weer).
"""

# --- INTERFACE (NEOBRUTALISM STYLE) ---
html_content = r"""
<!DOCTYPE html>
<html>
<head>
    <title>⚡ VIBE MANAGER OS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* RESET & BASE */
        * { box-sizing: border-box; }
        body { 
            background-color: #e0e7ff; 
            background-image: radial-gradient(#000 1px, transparent 1px);
            background-size: 20px 20px;
            font-family: 'Courier New', Courier, monospace; 
            margin: 0; 
            height: 100vh; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            padding: 20px;
        }

        /* MAIN CONTAINER */
        .layout {
            width: 100%;
            max-width: 900px;
            height: 90vh;
            background: #fff;
            border: 4px solid #000;
            box-shadow: 10px 10px 0px #000;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* HEADER */
        .header {
            background: #ccff00; /* Acid Green */
            border-bottom: 4px solid #000;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { 
            margin: 0; 
            font-size: 1.5rem; 
            font-weight: 900; 
            text-transform: uppercase; 
            letter-spacing: -1px;
        }
        .badge {
            background: #000;
            color: #fff;
            padding: 5px 10px;
            font-weight: bold;
            font-size: 0.8rem;
        }

        /* CHAT AREA */
        .chat { 
            flex: 1; 
            overflow-y: auto; 
            padding: 30px; 
            background: #fff;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* BUBBLES */
        .msg { 
            padding: 15px 20px; 
            max-width: 80%; 
            font-size: 1rem;
            line-height: 1.6;
            position: relative;
        }
        
        .model { 
            align-self: flex-start; 
            background: #ff90e8; /* Hot Pink */
            border: 3px solid #000;
            box-shadow: 5px 5px 0px #000;
            margin-right: auto;
        }
        
        .user { 
            align-self: flex-end; 
            background: #333; 
            color: #fff;
            border: 3px solid #000;
            box-shadow: -5px 5px 0px rgba(0,0,0,0.5);
        }

        /* CONTROLS */
        .controls { 
            padding: 20px; 
            background: #ccff00; 
            border-top: 4px solid #000;
            display: flex; 
            gap: 15px; 
        }

        input { 
            flex: 1; 
            padding: 15px; 
            font-family: inherit; 
            font-weight: bold;
            font-size: 1rem;
            border: 3px solid #000;
            outline: none;
        }
        input:focus {
            box-shadow: 4px 4px 0px #000;
            transform: translate(-2px, -2px);
        }

        button { 
            padding: 15px 30px; 
            background: #000; 
            color: #fff; 
            border: 3px solid #000; 
            font-family: inherit; 
            font-weight: 900; 
            font-size: 1rem;
            cursor: pointer; 
            box-shadow: 5px 5px 0px #fff; 
        }
        button:active {
            transform: translate(4px, 4px);
            box-shadow: 1px 1px 0px #fff;
        }

        /* SCROLLBAR & MOBILE */
        ::-webkit-scrollbar { width: 15px; }
        ::-webkit-scrollbar-track { background: #fff; border-left: 3px solid #000; }
        ::-webkit-scrollbar-thumb { background: #000; border: 2px solid #fff; }
        @media (max-width: 600px) {
            .layout { height: 100vh; max-width: 100%; border: none; box-shadow: none; }
            .msg { max-width: 90%; }
        }
    </style>
</head>
<body>
    <div class="layout">
        <div class="header">
            <h1>👾 Vibe Manager</h1>
            <div class="badge">LIVE SEARCH ACTIVE</div>
        </div>
        
        <div class="chat" id="chat">
            <div class="msg model">
                <strong>SYSTEM READY.</strong><br>
                Ik ben je Neobrutalist Vibe Manager.<br>
                Google Search is aangesloten.<br>
                Drop je commando. 👇
            </div>
        </div>
        
        <div class="controls">
            <input type="text" id="in" placeholder="Typ iets..." onkeypress="if(event.key==='Enter') send()">
            <button onclick="send()">SEND</button>
        </div>
    </div>

    <script>
        let hist = [];
        async function send() {
            let i = document.getElementById("in");
            let c = document.getElementById("chat");
            let t = i.value.trim(); if(!t) return;
            
            c.innerHTML += `<div class="msg user">${t}</div>`;
            i.value = "";
            
            let loadId = "load" + Date.now();
            c.innerHTML += `<div class="msg model" id="${loadId}" style="background:#fff; font-style:italic;">... LOADING DATA ...</div>`;
            c.scrollTop = c.scrollHeight;
            
            hist.push({role: "user", parts: [t]});
            
            try {
                let r = await fetch("/chat", {method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({history: hist})});
                let d = await r.json();
                document.getElementById(loadId).remove();
                
                let txt = d.response
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/### (.*?)\n/g, '<h3 style="margin:5px 0; border-bottom:2px solid #000;">$1</h3>')
                    .replace(/\n/g, '<br>');
                    
                c.innerHTML += `<div class="msg model">${txt}</div>`;
                hist.push({role: "model", parts: [d.response]});
            } catch(e) {
                let el = document.getElementById(loadId);
                if(el) {
                    el.innerText = "SYSTEM ERROR: " + e;
                    el.style.background = "red";
                    el.style.color = "white";
                }
            }
            c.scrollTop = c.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- PYTHON LOGICA ---
class Message(BaseModel):
    role: str
    parts: List[str]

class ChatRequest(BaseModel):
    history: List[Message]

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        contents = []
        for msg in req.history:
            contents.append(types.Content(
                role=msg.role,
                parts=[types.Part(text=p) for p in msg.parts]
            ))

        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        return {"response": response.text}
    except Exception as e:
        return {"response": f"Foutmelding: {str(e)}"}