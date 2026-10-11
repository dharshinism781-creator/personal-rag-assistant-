from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from dotenv import load_dotenv
from groq import Groq

from ingest import extract_text
from chunking import chunk_text
from retrieve import add_document, search
from dates import extract_dates, get_timeline

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(file_path)
    chunks = chunk_text(text)
    add_document(doc_id=file.filename, filename=file.filename, chunks=chunks)
    found = extract_dates(groq_client, text, file.filename)

    return {
        "status": "success",
        "filename": file.filename,
        "chunks_added": len(chunks),
        "dates_found": found,
    }

@app.post("/ask")
async def ask_question(question: str):
    results = search(question, top_k=3)
    retrieved_chunks = results["documents"][0]
    sources = results["metadatas"][0]

    context = "\n\n".join(retrieved_chunks)
    prompt = f"""Answer the question using ONLY the context below.
If the answer isn't in the context, say "I don't have that information in your documents."

Context:
{context}

Question: {question}

Answer:"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "sources": [s["source"] for s in sources]
    }

@app.get("/timeline")
async def timeline():
    return get_timeline()