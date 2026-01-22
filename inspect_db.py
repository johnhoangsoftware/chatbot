import sys
import os

# Adds the current directory to the path so we can import from app
sys.path.append(os.getcwd())

from app.services.vector_store import VectorStore

def inspect_db():
    print("="*50)
    print("🔍 Inspecting Vector Store (ChromaDB)...")
    print("="*50)
    print("Connecting to ChromaDB...")
    try:
        vs = VectorStore()
        collection = vs.collection
        
        count = collection.count()
        print(f"\n📊 Total chunks in database: {count}")
        
        if count == 0:
            print("Database is empty.")
            return

        # Get unique documents
        print("\n📑 Indexed Documents:")
        result = collection.get(include=["metadatas"])
        seen_docs = set()
        doc_count = 0
        
        for meta in result["metadatas"]:
            if not meta: continue
            
            doc_id = meta.get("document_id")
            filename = meta.get("filename", "Unknown")
            
            if doc_id and doc_id not in seen_docs:
                seen_docs.add(doc_id)
                doc_count += 1
                source_type = meta.get("source_type", "unknown")
                print(f"  {doc_count}. {filename} (ID: {doc_id}, Type: {source_type})")

        print(f"\n--- Total unique documents: {len(seen_docs)} ---")

        # Show sample chunks
        print("\n📝 Sample Chunks (First 3):")
        peek = collection.peek(limit=3)
        
        for i in range(len(peek['ids'])):
            print(f"\n[Chunk {i+1}] ID: {peek['ids'][i]}")
            print(f"Metadata: {peek['metadatas'][i]}")
            content = peek['documents'][i]
            # Truncate content for display
            display_content = content[:200] + "..." if len(content) > 200 else content
            print(f"Content: {display_content}")
            print("-" * 50)

    except Exception as e:
        print(f"❌ Error inspecting VectorDB: {e}")

def inspect_sqlite():
    print("\n\n" + "="*50)
    print("🔍 Inspecting SQLite Database (document.db)...")
    print("="*50)
    
    try:
        from app.rag.db.database import get_document_db
        from app.rag.db.models import RawDocument, DocumentChunk
        
        db = get_document_db()
        
        # Get Stats
        stats = db.get_stats()
        print(f"\n📊 Database Statistics:")
        print(f"- Total Raw Documents: {stats['total_documents']}")
        print(f"- Total Chunks: {stats['total_chunks']}")
        
        if stats['documents_by_source']:
            print("- Documents by Source:")
            for source, count in stats['documents_by_source'].items():
                print(f"  • {source}: {count}")
        
        if stats['total_documents'] == 0:
            print("\nDatabase is empty.")
            return

        # List Documents
        print("\n📑 Raw Documents in SQLite:")
        docs = db.list_raw_documents(limit=10)
        
        for i, doc in enumerate(docs, 1):
            print(f"\n  {i}. {doc.source_name}")
            print(f"     ID: {doc.id}")
            print(f"     Type: {doc.source_type}")
            print(f"     Path: {doc.source_path}")
            print(f"     Created: {doc.created_at}")
            print(f"     Chunks: {len(doc.chunks)}")
            print(f"     Preview: {doc.content[:100].replace(chr(10), ' ')}...")

        if stats['total_documents'] > 10:
            print(f"\n... and {stats['total_documents'] - 10} more documents.")

    except Exception as e:
        print(f"❌ Error inspecting SQLite: {e}")

if __name__ == "__main__":
    inspect_db()
    inspect_sqlite()
