// ========================================
// Automotive Chatbot POC - Frontend App
// ========================================

const API_BASE = '/api';
let sessionId = 'session_' + Date.now();
let documents = [];

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    setupFileUpload();
    setupTermSearch();
    loadDocuments();
    autoResizeTextarea();
});

// ========================================
// File Upload
// ========================================
function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // File selected
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
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
            uploadFile(e.dataTransfer.files[0]);
        }
    });
}

async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Only PDF files are supported!');
        return;
    }

    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = uploadProgress.querySelector('.progress-fill');
    const progressText = uploadProgress.querySelector('.progress-text');

    uploadProgress.classList.remove('hidden');
    progressFill.style.width = '30%';
    progressText.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        progressFill.style.width = '60%';
        progressText.textContent = 'Processing...';

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();

        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';

        // Reload documents
        await loadDocuments();

        // Add success message to chat
        addMessage('assistant', `📄 **${result.filename}** uploaded successfully!\n\n- Pages: ${result.page_count}\n- Chunks created: ${result.chunks_created}\n\nYou can now ask questions about this document.`);

        setTimeout(() => {
            uploadProgress.classList.add('hidden');
            progressFill.style.width = '0%';
        }, 2000);

    } catch (error) {
        progressText.textContent = `Error: ${error.message}`;
        progressFill.style.width = '0%';

        setTimeout(() => {
            uploadProgress.classList.add('hidden');
        }, 3000);
    }
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
                <h4>📚 Sources</h4>
                ${sources.map(s => `<span class="source-tag">${s.filename} (${(s.relevance_score * 100).toFixed(0)}%)</span>`).join('')}
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
