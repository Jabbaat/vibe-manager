import os
from pathlib import Path
from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv

# --- 1. DE .ENV ZOEKER ---
# We kijken 2 mappen omhoog om zeker te zijn (vanuit vibe_manager > naar hoofdmap)
current_dir = Path(__file__).parent
env_path = current_dir.parent / '.env'
load_dotenv(dotenv_path=env_path)

print("\n🚀 VIBE MANAGER LAADT IN...")

# --- 2. DE CHECK ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(f"❌ FOUT: Kan .env niet vinden op: {env_path}")
else:
    print(f"✅ SUCCES: Sleutel gevonden! (Begint met {api_key[:4]}...)")

# --- 3. DE AGENT ---
# We noemen de variabele 'vibe_agent'
vibe_agent = Agent(
    name="vibe_manager",
    model="gemini-1.5-flash",
    description="De assistent van EddieCool",
    instruction="""
    Je bent de Vibe Manager. 
    Antwoord kort, krachtig en met humor.
    Geef altijd 1 creatieve 'Vibe Tip' (video/web/AI).
    """,
)