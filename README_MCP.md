MCP Tools Enhancement & OpenWebUI Integration - Walkthrough
Summary
Đã tạo MCP server hoàn chỉnh với 16 tools để hỗ trợ Document RAG system và tích hợp với OpenWebUI.

Changes Made
1. Enhanced MCP Server
File: 
mcp_server.py

Category	Tool	Description
Search	search_documents	Tìm kiếm documents trong vector DB
Search	ask_question	Hỏi đáp với RAG
Docs	
list_documents
Liệt kê documents đã index
Docs	
get_document_info
Chi tiết document
Docs	
delete_document
Xóa document
Read	read_url	Đọc nội dung URL
Read	read_github_repo	Đọc GitHub repo
Read	read_file	Đọc file local
Ingest	
ingest_url
Ingest từ URL/GitHub
Ingest	
ingest_file
Ingest file local
Ingest	ingest_jira	Ingest từ Jira
Config	configure_chunking	Cấu hình chunking
Config	
get_chunking_config
Xem chunking config
DB	get_database_stats	Thống kê database
DB	clear_database	Xóa toàn bộ DB
Trace	trace_source	Truy vết nguồn chunk
2. HTTP Server for OpenWebUI
File: 
mcp_http_server.py

HTTP wrapper để OpenWebUI có thể gọi MCP tools (vì OpenWebUI không hỗ trợ stdio).

Endpoints:

GET /mcp/tools - Danh sách tools
POST /mcp/tools/{name} - Thực thi tool
GET /mcp/resources - Danh sách resources
GET /openwebui/tools - Format cho OpenWebUI
POST /openwebui/execute - Execute cho OpenWebUI
3. Configuration Files
openwebui_tools.json
 - Tool manifest
mcp_config.json
 - MCP server config
Usage
Option 1: MCP Stdio Mode (Claude Desktop, etc.)
cd C:\Users\johnh\OneDrive\Desktop\ChatBotDemo
python mcp_server.py
Option 2: HTTP Mode (OpenWebUI)
# Terminal 1: Start HTTP server
cd C:\Users\johnh\OneDrive\Desktop\ChatBotDemo
python mcp_http_server.py --port 8001
# Terminal 2: Test
curl http://localhost:8001/mcp/tools
curl -X POST http://localhost:8001/mcp/tools/list_documents -d "{}"
Option 3: OpenAI-Compatible API (Already exists)
# Start FastAPI server
uvicorn app.main:app --port 8000
# OpenWebUI connects to http://localhost:8000/v1
OpenWebUI Integration
Method A: OpenAI-Compatible API (Recommended)
Start app: uvicorn app.main:app --port 8000
In OpenWebUI → Settings → Connections → Add OpenAI Compatible
URL: http://localhost:8000/v1
Model: rag-model
Method B: MCP HTTP Server
Start: python mcp_http_server.py --port 8001
In OpenWebUI → Configure tools endpoint
URL: http://localhost:8001/openwebui/tools
Verification Commands
# Test MCP import
python -c "from mcp_server import list_tools; import asyncio; print(len(asyncio.run(list_tools())), 'tools loaded')"
# Test HTTP server
python mcp_http_server.py --port 8001
# In another terminal
curl http://localhost:8001/health
curl http://localhost:8001/mcp/tools
curl -X POST http://localhost:8001/mcp/tools/get_database_stats -H "Content-Type: application/json" -d "{}"


Tôi cần cấu trúc project phần query, làm sao để có thể link hoạt lựa chọ chiến lực query, dễ dàng scale hoặc kết hợp các chiến lực với nhau. Improve query hiện tai bằng một chiến lực nữa
