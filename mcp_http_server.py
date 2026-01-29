"""
MCP HTTP Server for OpenWebUI Integration.
Exposes MCP tools via HTTP REST API since OpenWebUI doesn't support stdio MCP.

Usage:
    python mcp_http_server.py --port 8001

Endpoints:
    GET  /mcp/tools              - List all available tools
    POST /mcp/tools/{tool_name}  - Execute a tool
    GET  /mcp/resources          - List available resources
    GET  /health                 - Health check
"""

import asyncio
import argparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn

# Import from main mcp_server
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server import (
    list_tools,
    call_tool,
    list_resources,
    get_chunking_config
)

app = FastAPI(
    title="MCP HTTP Server",
    description="HTTP wrapper for MCP tools - for OpenWebUI integration",
    version="1.0.0"
)

# CORS for OpenWebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToolCallRequest(BaseModel):
    """Request body for tool execution."""
    arguments: Dict[str, Any] = {}


class ToolInfo(BaseModel):
    """Tool information."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    result: str
    error: Optional[str] = None


class ResourceInfo(BaseModel):
    """Resource information."""
    uri: str
    name: str
    mimeType: str
    description: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp-http-server",
        "chunking_config": get_chunking_config()
    }


@app.get("/mcp/tools", response_model=List[ToolInfo])
async def get_tools():
    """List all available MCP tools."""
    tools = await list_tools()
    return [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            inputSchema=tool.inputSchema
        )
        for tool in tools
    ]


@app.post("/mcp/tools/{tool_name}", response_model=ToolCallResponse)
async def execute_tool(tool_name: str, request: ToolCallRequest):
    """Execute an MCP tool by name."""
    # Validate tool exists
    tools = await list_tools()
    tool_names = [t.name for t in tools]
    
    if tool_name not in tool_names:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available tools: {', '.join(tool_names)}"
        )
    
    try:
        results = await call_tool(tool_name, request.arguments)
        
        # Combine all text content
        result_text = "\n".join([r.text for r in results if hasattr(r, 'text')])
        
        return ToolCallResponse(
            success=True,
            result=result_text
        )
    except Exception as e:
        return ToolCallResponse(
            success=False,
            result="",
            error=str(e)
        )


@app.get("/mcp/resources", response_model=List[ResourceInfo])
async def get_resources():
    """List available resources (documents)."""
    resources = await list_resources()
    return [
        ResourceInfo(
            uri=r.uri,
            name=r.name,
            mimeType=r.mimeType,
            description=r.description
        )
        for r in resources
    ]


# === OpenWebUI Tools Format ===
# OpenWebUI expects a specific format for tools

@app.get("/openwebui/tools")
async def get_openwebui_tools():
    """
    Get tools in OpenWebUI format.
    This endpoint returns tool definitions compatible with OpenWebUI's tool system.
    """
    tools = await list_tools()
    
    openwebui_tools = []
    for tool in tools:
        openwebui_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        })
    
    return {
        "tools": openwebui_tools,
        "tool_choice": "auto"
    }


@app.post("/openwebui/execute")
async def execute_openwebui_tool(request: dict):
    """
    Execute a tool called by OpenWebUI.
    
    Expected request format:
    {
        "tool_calls": [
            {
                "function": {
                    "name": "tool_name",
                    "arguments": {...}
                }
            }
        ]
    }
    """
    tool_calls = request.get("tool_calls", [])
    
    if not tool_calls:
        raise HTTPException(status_code=400, detail="No tool calls provided")
    
    results = []
    for tc in tool_calls:
        func = tc.get("function", {})
        tool_name = func.get("name", "")
        arguments = func.get("arguments", {})
        
        # If arguments is a string, parse it as JSON
        if isinstance(arguments, str):
            import json
            try:
                arguments = json.loads(arguments)
            except:
                arguments = {}
        
        try:
            tool_results = await call_tool(tool_name, arguments)
            result_text = "\n".join([r.text for r in tool_results if hasattr(r, 'text')])
            results.append({
                "tool_call_id": tc.get("id", ""),
                "output": result_text
            })
        except Exception as e:
            results.append({
                "tool_call_id": tc.get("id", ""),
                "error": str(e)
            })
    
    return {"tool_results": results}


def main():
    parser = argparse.ArgumentParser(description="MCP HTTP Server for OpenWebUI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    args = parser.parse_args()
    
    print(f"Starting MCP HTTP Server on http://{args.host}:{args.port}")
    print(f"OpenWebUI tools endpoint: http://localhost:{args.port}/openwebui/tools")
    print(f"MCP tools endpoint: http://localhost:{args.port}/mcp/tools")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
