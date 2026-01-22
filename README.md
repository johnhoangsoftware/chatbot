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


check db:
python inspect_db.py

Source → Ingestion* → RawStore* → Parsing* → StructureBuild → Chunking* → ChunkStore → Embedding* → VectorDB* → Query* → TraceBack
StructureBuild
TraceBack


#### Lớp 1 – Raw Data Layer
- Hash
- Versioning
- Parser version
#### Lớp 2 – Semantic Layer
- Structure chunking
- Fast chunking *
- Summary
- Entity extraction
- Knowledge graph
#### Lớp 3 – Retrieval Layer
- Embedding *
- Hybrid search
- Reranking
- Trace back

PostgreSQL do nhanh bổ rẻ
Neo4j dùng cho KB

Thay dổi chiến luọcwj lưu trữ chunking 

Model embedding:
Technical text - text-embedding-3-large
Code/API - voyager-embedding-2
Requirements/Entities - cohere-embed-v3-large
Tables/Numeric - voyage-large-2
Lưu 4 partitions của vectorDB -> query + top_k + rerank