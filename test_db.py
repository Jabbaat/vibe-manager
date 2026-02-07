from google.cloud import firestore
import os
import datetime

# 1. Setup
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
SESSION_ID = "eddie_session_v1"

print(f"🔌 Verbinden met project: {PROJECT_ID}...")

try:
    db = firestore.Client(project=PROJECT_ID)
    print("✅ Verbinding gemaakt!")
    
    # 2. Even een test-berichtje opslaan (zodat er iets te vinden is)
    print("💾 Test bericht opslaan...")
    doc_ref = db.collection("chats").document(SESSION_ID).collection("messages").document()
    doc_ref.set({
        "role": "system",
        "content": "Database Test Bericht",
        "timestamp": datetime.datetime.now()
    })
    print("✅ Opgeslagen!")

    # 3. DE CRUCIALE TEST (De query die net crashte)
    print("🐘 Geheugen ophalen met .get() en limit_to_last()...")
    
    # Dit is de exacte regel uit je nieuwe test_agent.py
    docs = db.collection("chats").document(SESSION_ID).collection("messages") \
             .order_by("timestamp", direction=firestore.Query.ASCENDING) \
             .limit_to_last(20) \
             .get()  # <--- HIER KIJKEN WE OF .get() WERKT

    count = 0
    for doc in docs:
        count += 1
        
    print(f"✅ GELUKT! Ik heb {count} berichten opgehaald zonder te crashen.")
    print("\nCONCLUSIE: De fix werkt. Je kunt deployen! 🚀")

except Exception as e:
    print("\n❌ TEST MISLUKT!")
    print(f"Foutmelding: {e}")
    print("\nCONCLUSIE: Niet deployen, de code is nog stuk.")
