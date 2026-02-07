from google.cloud import firestore
import os

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
SESSION_ID = "eddie_session_v1"

print(f"🧹 Database schoonmaken voor project: {PROJECT_ID}...")

try:
    db = firestore.Client(project=PROJECT_ID)
    
    # We pakken alle berichten in jouw sessie
    messages_ref = db.collection("chats").document(SESSION_ID).collection("messages")
    docs = messages_ref.stream()

    deleted = 0
    for doc in docs:
        print(f"🗑️ Verwijder bericht: {doc.to_dict().get('content', 'Unknown')}")
        doc.reference.delete()
        deleted += 1

    print(f"\n✅ KLAAR! {deleted} berichten verwijderd.")
    print("Je kunt je Vibe Manager nu weer veilig gebruiken!")

except Exception as e:
    print(f"❌ Fout bij schoonmaken: {e}")
