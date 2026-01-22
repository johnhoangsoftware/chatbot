"""
MCP Server for Document RAG System.
Exposes document search and Q&A as MCP tools.
"""

import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Import RAG services
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_chain import RAGChain
from app.services.vector_store import VectorStore
from app.config import get_settings

# Initialize server
server = Server("document-rag")

# Global instances
_vector_store = None
_rag_chain = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_rag_chain():
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = RAGChain()
    return _rag_chain


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_documents",
            description="Search for relevant documents in the vector database. Returns document chunks matching the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant documents"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ask_question",
            description="Ask a question about the uploaded documents. Uses RAG to retrieve relevant context and generate an answer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask about the documents"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all documents that have been uploaded and indexed.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_document_info",
            description="Get detailed information about a specific document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document"
                    }
                },
                "required": ["document_id"]
            }
        ),
        # New data ingestion tools
        Tool(
            name="read_url",
            description="Read and extract raw text content from a URL (web page).",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to read content from"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="read_github_repo",
            description="Read and list files from a GitHub repository. Returns file structure and contents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL (e.g., https://github.com/user/repo)"
                    },
                    "file_extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by file extensions (e.g., ['.py', '.md']). Empty for all files.",
                        "default": []
                    }
                },
                "required": ["repo_url"]
            }
        ),
        Tool(
            name="read_file",
            description="Read raw content from a local file (PDF, DOCX, TXT, Excel, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="ingest_url",
            description="Ingest content from a URL into the vector database for RAG queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to ingest (web page or GitHub repo)"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="ingest_file",
            description="Ingest a local file into the vector database for RAG queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to ingest"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "search_documents":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)
        
        vector_store = get_vector_store()
        results = vector_store.search(query, k=top_k)
        
        # Format results
        formatted = []
        for i, result in enumerate(results):
            formatted.append(f"**Result {i+1}:**\n{result.get('content', '')}\n---")
        
        return [TextContent(
            type="text",
            text="\n".join(formatted) if formatted else "No results found."
        )]
    
    elif name == "ask_question":
        question = arguments.get("question", "")
        
        rag_chain = get_rag_chain()
        result = rag_chain.query(question)
        
        answer = result.get("answer", "Sorry, I couldn't generate an answer.")
        sources = result.get("sources", [])
        
        response = f"**Answer:**\n{answer}"
        if sources:
            response += f"\n\n**Sources:** {', '.join(sources)}"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "list_documents":
        vector_store = get_vector_store()
        # Get unique document IDs from the collection
        collection = vector_store.collection
        results = collection.get(include=["metadatas"])
        
        # Extract unique documents
        docs = {}
        for meta in results.get("metadatas", []):
            if meta:
                doc_id = meta.get("document_id", "unknown")
                if doc_id not in docs:
                    docs[doc_id] = {
                        "filename": meta.get("filename", "Unknown"),
                        "source_type": meta.get("source_type", "file")
                    }
        
        if not docs:
            return [TextContent(type="text", text="No documents have been indexed yet.")]
        
        doc_list = [f"- {info['filename']} (ID: {doc_id})" for doc_id, info in docs.items()]
        return [TextContent(type="text", text=f"**Indexed Documents ({len(docs)}):**\n" + "\n".join(doc_list))]
    
    elif name == "get_document_info":
        document_id = arguments.get("document_id", "")
        
        vector_store = get_vector_store()
        collection = vector_store.collection
        
        # Query chunks for this document
        results = collection.get(
            where={"document_id": document_id},
            include=["metadatas"]
        )
        
        if not results.get("ids"):
            return [TextContent(type="text", text=f"Document '{document_id}' not found.")]
        
        meta = results["metadatas"][0] if results.get("metadatas") else {}
        chunk_count = len(results.get("ids", []))
        
        info = f"""**Document Info:**
- **ID:** {document_id}
- **Filename:** {meta.get('filename', 'Unknown')}
- **Source:** {meta.get('source_type', 'Unknown')}
- **Chunks:** {chunk_count}
- **Page Count:** {meta.get('page_count', 'N/A')}
"""
        return [TextContent(type="text", text=info)]
    
    elif name == "read_url":
        url = arguments.get("url", "")
        try:
            import requests
            from bs4 import BeautifulSoup
            import html2text
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Convert to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            content = h.handle(str(soup))
            
            return [TextContent(type="text", text=f"**Content from {url}:**\n\n{content[:10000]}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading URL: {str(e)}")]
    
    elif name == "read_github_repo":
        repo_url = arguments.get("repo_url", "")
        file_extensions = arguments.get("file_extensions", [])
        
        try:
            from app.rag.ingrest_service.adapters.github_adapter import GitHubAdapter
            
            adapter = GitHubAdapter(repo_url)
            documents = adapter.collect()
            
            result = f"**GitHub Repository: {repo_url}**\n\n"
            result += f"Found {len(documents)} files:\n\n"
            
            for doc in documents[:20]:  # Limit to first 20
                filename = doc.metadata.get("file_path", "unknown")
                if file_extensions and not any(filename.endswith(ext) for ext in file_extensions):
                    continue
                result += f"### {filename}\n```\n{doc.content[:500]}...\n```\n\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading GitHub repo: {str(e)}")]
    
    elif name == "read_file":
        file_path = arguments.get("file_path", "")
        
        try:
            from app.services.parsers import ParserFactory
            
            parsed = ParserFactory.parse(file_path)
            
            result = f"**File: {parsed.filename}**\n\n"
            result += f"- Pages: {len(parsed.pages)}\n"
            result += f"- Tables: {len(parsed.tables)}\n\n"
            result += f"**Content:**\n{parsed.content[:10000]}"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading file: {str(e)}")]
    
    elif name == "ingest_url":
        url = arguments.get("url", "")
        
        try:
            from app.services.ingestion_service import IngestionService
            
            service = IngestionService()
            
            if 'github.com' in url.lower():
                results = service.ingest_github(url)
                success_count = sum(1 for r in results if r.success)
                return [TextContent(type="text", text=f"Ingested GitHub repo: {success_count} files indexed successfully.")]
            else:
                result = service.ingest_url(url)
                if result.success:
                    return [TextContent(type="text", text=f"URL ingested successfully. {result.chunk_count} chunks created.")]
                else:
                    return [TextContent(type="text", text=f"Failed to ingest URL: {result.error}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error ingesting URL: {str(e)}")]
    
    elif name == "ingest_file":
        file_path = arguments.get("file_path", "")
        
        try:
            from app.services.ingestion_service import IngestionService
            
            service = IngestionService()
            result = service.ingest_file(file_path)
            
            if result.success:
                return [TextContent(type="text", text=f"File ingested successfully. {result.chunk_count} chunks created.")]
            else:
                return [TextContent(type="text", text=f"Failed to ingest file: {result.error}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error ingesting file: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (documents)."""
    vector_store = get_vector_store()
    collection = vector_store.collection
    results = collection.get(include=["metadatas"])
    
    resources = []
    seen_docs = set()
    
    for meta in results.get("metadatas", []):
        if meta:
            doc_id = meta.get("document_id", "")
            if doc_id and doc_id not in seen_docs:
                seen_docs.add(doc_id)
                resources.append(Resource(
                    uri=f"document://{doc_id}",
                    name=meta.get("filename", "Unknown"),
                    mimeType="text/plain",
                    description=f"Document: {meta.get('filename', 'Unknown')}"
                ))
    
    return resources


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
