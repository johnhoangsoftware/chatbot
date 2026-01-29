"""
MCP Server for Document RAG System.
Exposes document search, Q&A, and data ingestion as MCP tools.
Enhanced version with Jira, database management, and traceability tools.
"""

import asyncio
import json
from typing import Any, Optional
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

# Global chunking configuration
_chunking_config = {
    "strategy": "structure",  # "structure" or "fast"
    "chunk_size": 1000,
    "chunk_overlap": 200
}


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


def get_chunking_config():
    """Get current chunking configuration."""
    return _chunking_config.copy()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        # === Search & Query Tools ===
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
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID for conversation history (optional)",
                        "default": "mcp"
                    }
                },
                "required": ["question"]
            }
        ),
        
        # === Document Management Tools ===
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
        Tool(
            name="delete_document",
            description="Delete a document and all its chunks from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document to delete"
                    }
                },
                "required": ["document_id"]
            }
        ),
        
        # === Data Reading Tools ===
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
                    },
                    "github_token": {
                        "type": "string",
                        "description": "GitHub personal access token (optional, for private repos)"
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
        
        # === Ingestion Tools ===
        Tool(
            name="ingest_url",
            description="Ingest content from a URL into the vector database for RAG queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to ingest (web page or GitHub repo)"
                    },
                    "github_token": {
                        "type": "string",
                        "description": "GitHub token for private repositories (optional)"
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
        ),
        Tool(
            name="ingest_jira",
            description="Ingest issues from a Jira project into the vector database. Requires Jira credentials.",
            inputSchema={
                "type": "object",
                "properties": {
                    "jira_url": {
                        "type": "string",
                        "description": "Jira instance URL (e.g., https://your-domain.atlassian.net)"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address for Jira authentication"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "Jira API token"
                    },
                    "project_key": {
                        "type": "string",
                        "description": "Jira project key (e.g., 'PROJ')"
                    },
                    "jql": {
                        "type": "string",
                        "description": "Optional JQL query to filter issues"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of issues to fetch (default: 100)",
                        "default": 100
                    }
                },
                "required": ["jira_url", "email", "api_token"]
            }
        ),
        
        # === Configuration Tools ===
        Tool(
            name="configure_chunking",
            description="Configure the chunking strategy for document ingestion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "enum": ["structure", "fast"],
                        "description": "'structure' for semantic chunking, 'fast' for fixed-size chunking"
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Maximum chunk size in characters (default: 1000)"
                    },
                    "chunk_overlap": {
                        "type": "integer",
                        "description": "Overlap between chunks in characters (default: 200)"
                    }
                }
            }
        ),
        Tool(
            name="get_chunking_config",
            description="Get the current chunking configuration.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        
        # === Database Management Tools ===
        Tool(
            name="get_database_stats",
            description="Get statistics about the vector database including document and chunk counts.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_database",
            description="Clear all data from the vector database. CAUTION: This action cannot be undone!",
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be set to true to confirm deletion"
                    }
                },
                "required": ["confirm"]
            }
        ),
        
        # === Traceability Tools ===
        Tool(
            name="trace_source",
            description="Trace a chunk back to its original source document and location.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "The ID of the chunk to trace"
                    }
                },
                "required": ["chunk_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    global _chunking_config
    
    try:
        # === Search & Query Tools ===
        if name == "search_documents":
            query = arguments.get("query", "")
            top_k = arguments.get("top_k", 5)
            
            vector_store = get_vector_store()
            results = vector_store.search(query, k=top_k)
            
            # Format results with chunk IDs for traceability
            formatted = []
            for i, result in enumerate(results):
                chunk_id = result.get("id", "unknown")
                content = result.get("content", "")
                source = result.get("metadata", {}).get("filename", "Unknown")
                formatted.append(f"**Result {i+1}** (Chunk: {chunk_id[:8]}..., Source: {source}):\n{content}\n---")
            
            return [TextContent(
                type="text",
                text="\n".join(formatted) if formatted else "No results found."
            )]
        
        elif name == "ask_question":
            question = arguments.get("question", "")
            session_id = arguments.get("session_id", "mcp")
            
            rag_chain = get_rag_chain()
            result = rag_chain.query(question, session_id=session_id)
            
            answer = result.get("answer", "Sorry, I couldn't generate an answer.")
            sources = result.get("sources", [])
            
            response = f"**Answer:**\n{answer}"
            if sources:
                response += f"\n\n**Sources:** {', '.join(sources)}"
            
            return [TextContent(type="text", text=response)]
        
        # === Document Management Tools ===
        elif name == "list_documents":
            vector_store = get_vector_store()
            collection = vector_store.collection
            results = collection.get(include=["metadatas"])
            
            # Extract unique documents with counts
            docs = {}
            for meta in results.get("metadatas", []):
                if meta:
                    doc_id = meta.get("document_id", "unknown")
                    if doc_id not in docs:
                        docs[doc_id] = {
                            "filename": meta.get("filename", "Unknown"),
                            "source_type": meta.get("source_type", "file"),
                            "chunk_count": 1
                        }
                    else:
                        docs[doc_id]["chunk_count"] += 1
            
            if not docs:
                return [TextContent(type="text", text="No documents have been indexed yet.")]
            
            doc_list = [f"- **{info['filename']}** ({info['chunk_count']} chunks, Type: {info['source_type']}, ID: {doc_id[:8]}...)" 
                       for doc_id, info in docs.items()]
            return [TextContent(type="text", text=f"**Indexed Documents ({len(docs)}):**\n" + "\n".join(doc_list))]
        
        elif name == "get_document_info":
            document_id = arguments.get("document_id", "")
            
            vector_store = get_vector_store()
            collection = vector_store.collection
            
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
- **Source Type:** {meta.get('source_type', 'Unknown')}
- **Chunks:** {chunk_count}
- **Page Count:** {meta.get('page_count', 'N/A')}
"""
            return [TextContent(type="text", text=info)]
        
        elif name == "delete_document":
            document_id = arguments.get("document_id", "")
            
            vector_store = get_vector_store()
            collection = vector_store.collection
            
            # Get all chunk IDs for this document
            results = collection.get(
                where={"document_id": document_id},
                include=[]
            )
            
            if not results.get("ids"):
                return [TextContent(type="text", text=f"Document '{document_id}' not found.")]
            
            chunk_ids = results["ids"]
            collection.delete(ids=chunk_ids)
            
            return [TextContent(type="text", text=f"Deleted document '{document_id}' and {len(chunk_ids)} chunks.")]
        
        # === Data Reading Tools ===
        elif name == "read_url":
            url = arguments.get("url", "")
            try:
                import requests
                from bs4 import BeautifulSoup
                import html2text
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for script in soup(["script", "style"]):
                    script.decompose()
                
                h = html2text.HTML2Text()
                h.ignore_links = False
                content = h.handle(str(soup))
                
                return [TextContent(type="text", text=f"**Content from {url}:**\n\n{content[:10000]}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error reading URL: {str(e)}")]
        
        elif name == "read_github_repo":
            repo_url = arguments.get("repo_url", "")
            file_extensions = arguments.get("file_extensions", [])
            github_token = arguments.get("github_token")
            
            try:
                from app.rag.ingrest_service.adapters.github_adapter import GitHubAdapter
                
                adapter = GitHubAdapter(repo_url, github_token=github_token)
                documents = adapter.collect()
                
                result = f"**GitHub Repository: {repo_url}**\n\n"
                result += f"Found {len(documents)} files:\n\n"
                
                for doc in documents[:20]:
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
        
        # === Ingestion Tools ===
        elif name == "ingest_url":
            url = arguments.get("url", "")
            github_token = arguments.get("github_token")
            
            try:
                from app.services.ingestion_service import IngestionService
                
                service = IngestionService()
                
                if 'github.com' in url.lower():
                    from app.rag.ingrest_service.adapters.github_adapter import GitHubAdapter
                    adapter = GitHubAdapter(url, github_token=github_token)
                    results = service.ingest_from_adapter(
                        adapter,
                        chunking_strategy=_chunking_config["strategy"],
                        chunk_size=_chunking_config["chunk_size"],
                        chunk_overlap=_chunking_config["chunk_overlap"]
                    )
                    success_count = sum(1 for r in results if r.success)
                    total_chunks = sum(r.chunk_count for r in results if r.success)
                    return [TextContent(type="text", text=f"Ingested GitHub repo: {success_count} files, {total_chunks} chunks created.")]
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
                result = service.ingest_file(
                    file_path,
                    chunking_strategy=_chunking_config["strategy"],
                    chunk_size=_chunking_config["chunk_size"],
                    chunk_overlap=_chunking_config["chunk_overlap"]
                )
                
                if result.success:
                    return [TextContent(type="text", text=f"File ingested successfully. {result.chunk_count} chunks created.")]
                else:
                    return [TextContent(type="text", text=f"Failed to ingest file: {result.error}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error ingesting file: {str(e)}")]
        
        elif name == "ingest_jira":
            jira_url = arguments.get("jira_url", "")
            email = arguments.get("email", "")
            api_token = arguments.get("api_token", "")
            project_key = arguments.get("project_key")
            jql = arguments.get("jql")
            max_results = arguments.get("max_results", 100)
            
            try:
                from app.rag.ingrest_service.adapters.jira_adapter import JiraAdapter
                from app.services.ingestion_service import IngestionService
                
                adapter = JiraAdapter(
                    jira_url=jira_url,
                    email=email,
                    api_token=api_token,
                    project_key=project_key,
                    jql=jql,
                    max_results=max_results
                )
                
                # Validate connection first
                if not adapter.validate():
                    return [TextContent(type="text", text="Failed to connect to Jira. Please check your credentials.")]
                
                service = IngestionService()
                results = service.ingest_from_adapter(
                    adapter,
                    chunking_strategy=_chunking_config["strategy"],
                    chunk_size=_chunking_config["chunk_size"],
                    chunk_overlap=_chunking_config["chunk_overlap"]
                )
                
                success_count = sum(1 for r in results if r.success)
                total_chunks = sum(r.chunk_count for r in results if r.success)
                
                return [TextContent(type="text", text=f"Ingested Jira issues: {success_count} issues, {total_chunks} chunks created.")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error ingesting Jira: {str(e)}")]
        
        # === Configuration Tools ===
        elif name == "configure_chunking":
            if "strategy" in arguments:
                _chunking_config["strategy"] = arguments["strategy"]
            if "chunk_size" in arguments:
                _chunking_config["chunk_size"] = arguments["chunk_size"]
            if "chunk_overlap" in arguments:
                _chunking_config["chunk_overlap"] = arguments["chunk_overlap"]
            
            return [TextContent(type="text", text=f"Chunking configuration updated:\n" + 
                              f"- Strategy: {_chunking_config['strategy']}\n" +
                              f"- Chunk Size: {_chunking_config['chunk_size']}\n" +
                              f"- Chunk Overlap: {_chunking_config['chunk_overlap']}")]
        
        elif name == "get_chunking_config":
            return [TextContent(type="text", text=f"**Current Chunking Configuration:**\n" +
                              f"- Strategy: {_chunking_config['strategy']}\n" +
                              f"- Chunk Size: {_chunking_config['chunk_size']}\n" +
                              f"- Chunk Overlap: {_chunking_config['chunk_overlap']}")]
        
        # === Database Management Tools ===
        elif name == "get_database_stats":
            vector_store = get_vector_store()
            collection = vector_store.collection
            results = collection.get(include=["metadatas"])
            
            # Count unique documents and total chunks
            doc_ids = set()
            source_types = {}
            for meta in results.get("metadatas", []):
                if meta:
                    doc_id = meta.get("document_id", "unknown")
                    doc_ids.add(doc_id)
                    source_type = meta.get("source_type", "unknown")
                    source_types[source_type] = source_types.get(source_type, 0) + 1
            
            total_chunks = len(results.get("ids", []))
            
            stats = f"""**Database Statistics:**
- **Total Documents:** {len(doc_ids)}
- **Total Chunks:** {total_chunks}
- **By Source Type:**
"""
            for src_type, count in source_types.items():
                stats += f"  - {src_type}: {count} chunks\n"
            
            return [TextContent(type="text", text=stats)]
        
        elif name == "clear_database":
            confirm = arguments.get("confirm", False)
            
            if not confirm:
                return [TextContent(type="text", text="Database clear ABORTED. Set 'confirm' to true to proceed.")]
            
            vector_store = get_vector_store()
            collection = vector_store.collection
            
            # Get all IDs and delete
            results = collection.get(include=[])
            all_ids = results.get("ids", [])
            
            if not all_ids:
                return [TextContent(type="text", text="Database is already empty.")]
            
            collection.delete(ids=all_ids)
            
            return [TextContent(type="text", text=f"Database cleared. Deleted {len(all_ids)} chunks.")]
        
        # === Traceability Tools ===
        elif name == "trace_source":
            chunk_id = arguments.get("chunk_id", "")
            
            vector_store = get_vector_store()
            collection = vector_store.collection
            
            # Get chunk by ID
            results = collection.get(
                ids=[chunk_id],
                include=["metadatas", "documents"]
            )
            
            if not results.get("ids"):
                return [TextContent(type="text", text=f"Chunk '{chunk_id}' not found.")]
            
            meta = results["metadatas"][0] if results.get("metadatas") else {}
            content = results["documents"][0] if results.get("documents") else ""
            
            trace_info = f"""**Chunk Trace Information:**
- **Chunk ID:** {chunk_id}
- **Document ID:** {meta.get('document_id', 'Unknown')}
- **Filename:** {meta.get('filename', 'Unknown')}
- **Source Type:** {meta.get('source_type', 'Unknown')}
- **Source Path:** {meta.get('source_path', 'Unknown')}
- **Chunk Index:** {meta.get('chunk_index', 'N/A')}
- **Page Number:** {meta.get('page_number', 'N/A')}

**Content Preview:**
{content[:500]}...
"""
            return [TextContent(type="text", text=trace_info)]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool '{name}': {str(e)}")]


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
