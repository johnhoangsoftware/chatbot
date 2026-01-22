// ========================================
// Automotive Chatbot POC - Frontend App
// ========================================

const API_BASE = '/api';
let sessionId = 'session_' + Date.now();
let documents = [];
let hasDocuments = false;

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    // Initial setup
    setupFileUpload();
    setupTermSearch();
    loadDocuments(); // Check for existing docs
    autoResizeTextarea();

    // Check initial view state
    updateViewState();
});

// ========================================
// View Management
// ========================================
function switchView(viewName) {
    const uploadView = document.getElementById('uploadView');
    const chatView = document.getElementById('chatView');

    if (viewName === 'chat') {
        if (!hasDocuments) {
            alert('Please upload a document to start chatting.');
            return;
        }
        uploadView.classList.add('hidden');
        chatView.classList.remove('hidden');

        // Scroll to bottom of chat
        scrollToBottom();
    } else {
        chatView.classList.add('hidden');
        uploadView.classList.remove('hidden');
    }
}

function switchToChat() {
    switchView('chat');
}

function switchToUpload() {
    switchView('upload');
}

function updateViewState() {
    const startChatBtn = document.getElementById('startChatBtn');

    if (documents.length > 0) {
        hasDocuments = true;
        startChatBtn.disabled = false;
        startChatBtn.innerHTML = 'Start Chatting 💬';
    } else {
        hasDocuments = false;
        startChatBtn.disabled = true;
        startChatBtn.innerHTML = 'Start Chatting 💬 (Upload Docs First)';
    }
}

// ========================================
// File Upload
// ========================================
function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // File selected (multiple files)
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            uploadMultipleFiles(files);
        }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadMultipleFiles(Array.from(e.dataTransfer.files));
        }
    });
}
// Upload queue state
let uploadQueue = [];
let isUploading = false;

// Multi-file upload handler
async function uploadMultipleFiles(files) {
    // Filter supported file types
    const supportedExtensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md'];
    const validFiles = files.filter(f => {
        const ext = f.name.toLowerCase().substring(f.name.lastIndexOf('.'));
        return supportedExtensions.includes(ext);
    });

    if (validFiles.length === 0) {
        alert('Please select supported file types: PDF, Word (DOCX/DOC), Excel (XLSX/XLS), or Text (TXT/MD)');
        return;
    }

    if (validFiles.length < files.length) {
        alert(`${files.length - validFiles.length} file(s) skipped. Only PDF, Word, Excel, and Text files are supported.`);
    }

    // Initialize queue
    uploadQueue = validFiles.map((file, index) => ({
        id: `upload_${Date.now()}_${index}`,
        file: file,
        status: 'pending',
        stage: 0,  // 0: pending, 1: uploading, 2: parsing, 3: chunking, 4: done
        progress: 0,
        result: null,
        error: null
    }));

    // Show queue UI
    renderUploadQueue();

    // Process files sequentially
    await processUploadQueue();
}

function renderUploadQueue() {
    // We now have a centered queue for the main view
    const queueContainer = document.getElementById('mainQueueContent');
    const queueWrapper = document.getElementById('mainUploadQueue');

    if (queueWrapper) {
        queueWrapper.classList.remove('hidden');
    }

    // Also update sidebar queue if it exists (for when in chat view)
    const sidebarQueue = document.getElementById('uploadQueue');
    if (sidebarQueue) {
        sidebarQueue.classList.remove('hidden');
    }

    const html = uploadQueue.map(item => `
        <div class="upload-queue-item" id="upload-item-${item.id}">
            <div class="upload-queue-header">
                <div class="upload-queue-filename">
                    <span>📄</span>
                    <span title="${item.file.name}">${truncateFilename(item.file.name, 25)}</span>
                </div>
                <span class="upload-queue-status status-${item.status}">${getStatusLabel(item.status)}</span>
            </div>
            <div class="analysis-stages">
                <div class="analysis-stage">
                    <div class="stage-indicator ${item.stage >= 1 ? (item.stage > 1 ? 'stage-complete' : 'stage-active') : ''}">📤</div>
                    <div class="stage-label ${item.stage >= 1 ? (item.stage > 1 ? 'stage-complete' : 'stage-active') : ''}">Upload</div>
                </div>
                <div class="analysis-stage">
                    <div class="stage-indicator ${item.stage >= 2 ? (item.stage > 2 ? 'stage-complete' : 'stage-active') : ''}">📖</div>
                    <div class="stage-label ${item.stage >= 2 ? (item.stage > 2 ? 'stage-complete' : 'stage-active') : ''}">Parse</div>
                </div>
                <div class="analysis-stage">
                    <div class="stage-indicator ${item.stage >= 3 ? (item.stage > 3 ? 'stage-complete' : 'stage-active') : ''}">✂️</div>
                    <div class="stage-label ${item.stage >= 3 ? (item.stage > 3 ? 'stage-complete' : 'stage-active') : ''}">Chunk</div>
                </div>
                <div class="analysis-stage">
                    <div class="stage-indicator ${item.stage >= 4 ? 'stage-complete' : ''}">✅</div>
                    <div class="stage-label ${item.stage >= 4 ? 'stage-complete' : ''}">Done</div>
                </div>
            </div>
            <div class="upload-progress-bar">
                <div class="upload-progress-fill" style="width: ${item.progress}%"></div>
            </div>
        </div>
    `).join('');

    if (queueContainer) queueContainer.innerHTML = html;
    if (sidebarQueue) sidebarQueue.innerHTML = html;
}

function truncateFilename(name, maxLen) {
    if (name.length <= maxLen) return name;
    const ext = name.split('.').pop();
    const baseName = name.slice(0, name.length - ext.length - 1);
    const truncated = baseName.slice(0, maxLen - ext.length - 4) + '...';
    return truncated + '.' + ext;
}

function getStatusLabel(status) {
    const labels = {
        'pending': 'Waiting',
        'uploading': 'Uploading',
        'processing': 'Processing',
        'done': 'Complete',
        'error': 'Error'
    };
    return labels[status] || status;
}

function updateQueueItem(itemId, updates) {
    const item = uploadQueue.find(i => i.id === itemId);
    if (item) {
        Object.assign(item, updates);
        renderUploadQueue();
    }
}

async function processUploadQueue() {
    if (isUploading) return;
    isUploading = true;

    for (const item of uploadQueue) {
        if (item.status !== 'pending') continue;

        try {
            // Stage 1: Uploading
            updateQueueItem(item.id, { status: 'uploading', stage: 1, progress: 20 });

            const formData = new FormData();
            formData.append('file', item.file);

            // Stage 2: Parsing (simulate - actual parsing happens server-side but we simulate progress)
            updateQueueItem(item.id, { status: 'processing', stage: 2, progress: 50 });

            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });

            // Stage 3: Chunking
            updateQueueItem(item.id, { stage: 3, progress: 75 });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();

            // Stage 4: Done
            updateQueueItem(item.id, {
                status: 'done',
                stage: 4,
                progress: 100,
                result: result
            });

        } catch (error) {
            updateQueueItem(item.id, {
                status: 'error',
                error: error.message
            });
        }
    }

    isUploading = false;

    // Reload documents
    await loadDocuments();

    // Show summary message
    const successful = uploadQueue.filter(i => i.status === 'done');
    const failed = uploadQueue.filter(i => i.status === 'error');

    if (successful.length > 0) {
        const totalChunks = successful.reduce((sum, i) => sum + (i.result?.chunks_created || 0), 0);
        let msg = `📄 **${successful.length} file(s) uploaded successfully!**\n\n`;
        msg += successful.map(i => `- ${i.file.name}: ${i.result?.chunks_created || 0} chunks`).join('\n');
        msg += `\n\n**Total chunks created:** ${totalChunks}`;
        addMessage('assistant', msg);
    }

    if (failed.length > 0) {
        let msg = `❌ **${failed.length} file(s) failed:**\n\n`;
        msg += failed.map(i => `- ${i.file.name}: ${i.error}`).join('\n');
        addMessage('assistant', msg);
    }

    // Hide queue after delay
    setTimeout(() => {
        const queueWrapper = document.getElementById('mainUploadQueue');
        if (queueWrapper) queueWrapper.classList.add('hidden');

        const sidebarQueue = document.getElementById('uploadQueue');
        if (sidebarQueue) sidebarQueue.classList.add('hidden');

        uploadQueue = [];
    }, 4000); // Increased delay to 4s to let user see completion
}

// ========================================
// URL Upload
// ========================================
async function uploadFromUrl() {
    const urlInput = document.getElementById('urlInput');
    const statusDiv = document.getElementById('urlUploadStatus');
    const statusIcon = statusDiv.querySelector('.status-icon');
    const statusMessage = statusDiv.querySelector('.status-message');

    const url = urlInput.value.trim();

    if (!url) {
        showUrlStatus('error', '⚠️', 'Vui lòng nhập URL');
        return;
    }

    // Basic URL validation
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        showUrlStatus('error', '⚠️', 'URL phải bắt đầu bằng http:// hoặc https://');
        return;
    }

    // Show loading
    showUrlStatus('loading', '⏳', 'Đang tải nội dung từ URL...');

    try {
        const response = await fetch(`${API_BASE}/upload-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const result = await response.json();

        if (result.success) {
            showUrlStatus('success', '✅', `Đã tải thành công! ${result.chunks_created} chunks được tạo.`);
            urlInput.value = '';

            // Reload documents
            await loadDocuments();

            // Add success message to chat
            const title = result.title || url;
            addMessage('assistant', `🔗 **${title}** đã được tải thành công từ URL!\n\n- Nguồn: ${result.source_type || 'web'}\n- Chunks created: ${result.chunks_created}\n\nBạn có thể hỏi về nội dung này ngay bây giờ.`);

            // Hide status after delay
            setTimeout(() => {
                statusDiv.classList.add('hidden');
            }, 5000);
        } else {
            // Show error with Vietnamese message
            const errorMsg = result.error_detail || result.message || 'Lỗi không xác định';
            showUrlStatus('error', '❌', errorMsg);

            // Add error to chat for visibility
            addMessage('assistant', `❌ **Lỗi tải URL**\n\n${errorMsg}\n\n🔹 Mã lỗi: ${result.error_code || 'UNKNOWN'}`);
        }

    } catch (error) {
        showUrlStatus('error', '❌', `Lỗi kết nối: ${error.message}`);
    }
}

function showUrlStatus(type, icon, message) {
    const statusDiv = document.getElementById('urlUploadStatus');
    const statusIcon = statusDiv.querySelector('.status-icon');
    const statusMessage = statusDiv.querySelector('.status-message');

    statusDiv.classList.remove('hidden', 'status-success', 'status-error', 'status-loading');
    statusDiv.classList.add(`status-${type}`);
    statusIcon.textContent = icon;
    statusMessage.textContent = message;
}

// ========================================
// Document Management
// ========================================
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();
        documents = data.documents || [];
        renderDocumentList();
        updateCompareSelects();
        updateViewState(); // Update view state based on document count
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function renderDocumentList() {
    const list = document.getElementById('documentList');

    if (documents.length === 0) {
        list.innerHTML = '<p class="no-docs">No documents uploaded</p>';
        return;
    }

    list.innerHTML = documents.map(doc => `
        <div class="document-item" data-id="${doc.document_id}">
            <span class="document-icon">📄</span>
            <div class="document-info">
                <div class="document-name" title="${doc.filename}">${doc.filename}</div>
                <div class="document-meta">${doc.chunk_count} chunks</div>
            </div>
            <button class="document-delete" onclick="deleteDocument('${doc.document_id}')" title="Delete">🗑️</button>
        </div>
    `).join('');
}

async function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadDocuments();
            addMessage('assistant', '🗑️ Document deleted successfully.');
        }
    } catch (error) {
        console.error('Error deleting document:', error);
    }
}

// ========================================
// Chat Functionality
// ========================================
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    const textarea = document.getElementById('chatInput');
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    });
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add user message
    addMessage('user', message);

    // Show typing indicator
    showTyping(true);

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                k: 5
            })
        });

        showTyping(false);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chat failed');
        }

        const result = await response.json();

        // Add assistant response with sources
        addMessage('assistant', result.answer, result.sources);

    } catch (error) {
        showTyping(false);
        addMessage('assistant', `❌ Error: ${error.message}`);
    }
}

function addMessage(role, content, sources = []) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const avatar = role === 'user' ? '👤' : '🤖';

    // Simple markdown-like formatting
    let formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <h4>📚 Sources (click to view details)</h4>
                ${sources.map(s => `
                    <span class="source-tag" onclick="traceSource('${s.document_id}')" data-doc-id="${s.document_id}">
                        <span class="source-icon">📄</span>
                        ${s.filename}
                        <span class="source-score">${(s.relevance_score * 100).toFixed(0)}%</span>
                    </span>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${formattedContent}</p>
            ${sourcesHtml}
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

function showTyping(show) {
    const indicator = document.getElementById('typingIndicator');
    if (show) {
        indicator.classList.remove('hidden');
        scrollToBottom();
    } else {
        indicator.classList.add('hidden');
    }
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    container.scrollTop = container.scrollHeight;
}

function clearChat() {
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="message message-assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <p>Chat cleared. Ready for new questions!</p>
            </div>
        </div>
    `;

    // Clear session on server
    fetch(`${API_BASE}/chat/clear/${sessionId}`, { method: 'POST' });

    // Generate new session
    sessionId = 'session_' + Date.now();
}

// ========================================
// Term Search
// ========================================
function setupTermSearch() {
    const termSearch = document.getElementById('termSearch');
    let debounceTimer;

    termSearch.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            searchTerms(e.target.value);
        }, 300);
    });
}

async function searchTerms(query) {
    const resultsDiv = document.getElementById('termResults');

    if (!query.trim()) {
        resultsDiv.innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/terms/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.results && data.results.length > 0) {
            resultsDiv.innerHTML = data.results.slice(0, 5).map(term => `
                <div class="term-item">
                    <strong>${term.term}</strong> (${term.domain})<br>
                    <small>${term.definition}</small>
                </div>
            `).join('');
        } else {
            resultsDiv.innerHTML = '<div class="term-item">No terms found</div>';
        }
    } catch (error) {
        console.error('Term search error:', error);
    }
}

function searchDomain(domain) {
    document.getElementById('termSearch').value = domain;
    searchTerms(domain);
}

// ========================================
// Document Comparison
// ========================================
function openCompareModal() {
    updateCompareSelects();
    document.getElementById('compareModal').classList.remove('hidden');
}

function closeCompareModal() {
    document.getElementById('compareModal').classList.add('hidden');
}

function updateCompareSelects() {
    const select1 = document.getElementById('compareDoc1');
    const select2 = document.getElementById('compareDoc2');

    const options = documents.map(doc =>
        `<option value="${doc.document_id}">${doc.filename}</option>`
    ).join('');

    const defaultOption = '<option value="">Select document...</option>';
    select1.innerHTML = defaultOption + options;
    select2.innerHTML = defaultOption + options;
}

async function compareDocuments() {
    const doc1 = document.getElementById('compareDoc1').value;
    const doc2 = document.getElementById('compareDoc2').value;
    const focus = document.getElementById('compareFocus').value;

    if (!doc1 || !doc2) {
        alert('Please select two documents to compare');
        return;
    }

    if (doc1 === doc2) {
        alert('Please select two different documents');
        return;
    }

    closeCompareModal();

    // Show loading in chat
    addMessage('assistant', '📊 Comparing documents... Please wait.');
    showTyping(true);

    try {
        const response = await fetch(`${API_BASE}/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id_1: doc1,
                document_id_2: doc2,
                focus_area: focus || null
            })
        });

        showTyping(false);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Comparison failed');
        }

        const result = await response.json();
        showCompareResults(result);

    } catch (error) {
        showTyping(false);
        addMessage('assistant', `❌ Comparison error: ${error.message}`);
    }
}

function showCompareResults(result) {
    const modal = document.getElementById('compareResultsModal');
    const body = document.getElementById('compareResultsBody');

    const differencesHtml = result.differences.map(diff => `
        <div class="difference-item">
            <div class="difference-category">${diff.category}</div>
            <div>${diff.description}</div>
        </div>
    `).join('');

    body.innerHTML = `
        <div class="comparison-summary">
            <h3>📋 Summary</h3>
            <p>${result.summary}</p>
            <div class="similarity-score">
                <span>Similarity:</span>
                <div class="score-bar">
                    <div class="score-fill" style="width: ${result.similarity_score * 100}%"></div>
                </div>
                <span class="score-value">${(result.similarity_score * 100).toFixed(0)}%</span>
            </div>
        </div>
        <div class="difference-list">
            <h3>🔍 Differences Found</h3>
            ${differencesHtml}
        </div>
        <p style="margin-top: 16px; color: var(--text-muted);">
            Documents compared: ${result.documents_compared.join(' vs ')}
        </p>
    `;

    modal.classList.remove('hidden');
}

function closeCompareResultsModal() {
    document.getElementById('compareResultsModal').classList.add('hidden');
}

// ========================================
// Source Tracing
// ========================================
let currentTraceDocId = null;

async function traceSource(documentId) {
    currentTraceDocId = documentId;

    try {
        // Fetch document details from traceability API
        const response = await fetch(`${API_BASE}/traceability/document/${documentId}`);

        if (!response.ok) {
            throw new Error('Failed to fetch document details');
        }

        const data = await response.json();
        showSourceTraceModal(data);

    } catch (error) {
        console.error('Trace source error:', error);
        alert(`Error loading source: ${error.message}`);
    }
}

function showSourceTraceModal(data) {
    const modal = document.getElementById('sourceTraceModal');
    const body = document.getElementById('sourceTraceBody');

    const chunksPreview = data.chunks && data.chunks.length > 0
        ? data.chunks.slice(0, 3).map((chunk, i) => `
            <div style="margin-bottom: 12px; padding: 10px; background: var(--bg-input); border-radius: 8px;">
                <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">Chunk ${chunk.chunk_index + 1}</div>
                <div style="font-size: 13px; line-height: 1.5;">${escapeHtml(chunk.content.substring(0, 300))}${chunk.content.length > 300 ? '...' : ''}</div>
            </div>
        `).join('')
        : '<p style="color: var(--text-muted);">No chunks available</p>';

    body.innerHTML = `
        <div class="source-trace-info">
            <div class="source-trace-field">
                <label>Document Name</label>
                <div class="value">${data.source_name || 'Unknown'}</div>
            </div>
            <div class="source-trace-field">
                <label>Source Type</label>
                <div class="value">${data.source_type || 'file'}</div>
            </div>
            <div class="source-trace-field">
                <label>Source Path</label>
                <div class="value" style="word-break: break-all; font-size: 12px;">${data.source_path || 'N/A'}</div>
            </div>
            <div class="source-trace-field">
                <label>Total Chunks</label>
                <div class="value">${data.chunks ? data.chunks.length : 0}</div>
            </div>
        </div>
        
        <div class="source-content-preview">
            <h4>📝 Content Preview</h4>
            <div class="content-text">${escapeHtml(data.content_preview || 'No preview available')}</div>
        </div>
        
        <div style="margin-top: 20px;">
            <h4 style="font-size: 12px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 12px;">📦 Chunks Used</h4>
            ${chunksPreview}
            ${data.chunks && data.chunks.length > 3 ? `<p style="font-size: 12px; color: var(--text-muted);">And ${data.chunks.length - 3} more chunks...</p>` : ''}
        </div>
    `;

    modal.classList.remove('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function closeSourceTraceModal() {
    document.getElementById('sourceTraceModal').classList.add('hidden');
    currentTraceDocId = null;
}

async function viewFullDocument() {
    if (!currentTraceDocId) return;

    try {
        const response = await fetch(`${API_BASE}/traceability/document/${currentTraceDocId}/content`);

        if (!response.ok) {
            throw new Error('Failed to fetch document content');
        }

        const data = await response.json();

        // Open in new window/tab or could display in a larger modal
        const contentWindow = window.open('', '_blank');
        contentWindow.document.write(`
            <html>
            <head>
                <title>${data.source_name || 'Document'}</title>
                <style>
                    body { font-family: 'Inter', sans-serif; padding: 40px; max-width: 900px; margin: 0 auto; line-height: 1.8; background: #1a1a2e; color: #e0e0e0; }
                    h1 { color: #667eea; font-size: 24px; margin-bottom: 20px; }
                    pre { white-space: pre-wrap; word-wrap: break-word; background: #252542; padding: 20px; border-radius: 8px; }
                </style>
            </head>
            <body>
                <h1>📄 ${data.source_name || 'Document'}</h1>
                <pre>${escapeHtml(data.content)}</pre>
            </body>
            </html>
        `);
        contentWindow.document.close();

    } catch (error) {
        alert(`Error loading full document: ${error.message}`);
    }
}
