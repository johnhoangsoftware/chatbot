# ingest_service/chunking.py
# fast chunking of documents
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

def chunk(raw_doc):
    chunks = splitter.split_text(raw_doc["content"])
    output = []

    for idx, text in enumerate(chunks):
        output.append({
            "chunk_id": raw_doc["raw_id"] + f"_c{idx}",
            "raw_id": raw_doc["raw_id"],
            "text": text,
            "metadata": raw_doc["metadata"] | {
                "chunk_index": idx,
                "source_type": raw_doc["source_type"],
                "path": raw_doc["path"]
            }
        })
    return output
