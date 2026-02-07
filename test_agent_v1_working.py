from fastapi import FastAPI
from pydantic import BaseModel
import os

# Import je agent
from agent import root_agent

app = FastAPI(title="Vibe Manager API")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    status: str

@app.get("/")
def home():
    return {
        "status": "🚀 Vibe Manager is LIVE!",
        "agent": "vibe_manager",
        "version": "1.0"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-flash-latest')
        
        full_prompt = f"""{root_agent.instruction}

Gebruiker: {request.message}"""
        
        response = model.generate_content(full_prompt)
        
        return ChatResponse(
            response=response.text,
            status="success"
        )
    except Exception as e:
        return ChatResponse(
            response=f"Error: {str(e)}",
            status="error"
        )

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "api_key_set": bool(os.getenv("GOOGLE_API_KEY"))
    }
