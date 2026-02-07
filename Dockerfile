FROM python:3.11-slim

WORKDIR /app

# We voegen google-cloud-firestore toe aan de lijst
RUN pip install --no-cache-dir --upgrade \
    fastapi \
    uvicorn[standard] \
    pydantic \
    python-dotenv \
    google-genai \
    python-multipart \
    python-docx \
    pandas \
    openpyxl \
    google-cloud-firestore

COPY test_agent.py .

CMD ["uvicorn", "test_agent:app", "--host", "0.0.0.0", "--port", "8080"]
