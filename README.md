# Automotive Chatbot POC

Chatbot RAG cho domain Automotive với khả năng đọc tài liệu và trả lời câu hỏi.

## Tech Stack
- **LLM**: Google Gemini AI
- **Vector DB**: ChromaDB
- **Backend**: FastAPI + LangChain
- **Document Parser**: PyMuPDF

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env và thêm GOOGLE_API_KEY
```

### 3. Run Application
```bash
python -m uvicorn app.main:app --reload
```

### 4. Open Browser
```
http://localhost:8000
```

## Features
- 📄 Upload PDF documents
- 💬 Chat với RAG
- 🔍 So sánh documents
- 📚 Domain dictionary (ASPICE, AUTOSAR, ISO26262)
