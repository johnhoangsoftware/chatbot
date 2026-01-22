// State
const API_BASE = '/api';
let selectedFiles = [];
let selectedLinks = [];
let messages = [];

// File Input Handler
document.getElementById('fileInput').addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        if (!selectedFiles.find(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    });
    updateFileList();
    updateAnalyzeButton();
});

// Update File List Display
function updateFileList() {
    const fileList = document.getElementById('fileList');
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '<div style="color: var(--text-light); font-size: 13px;">No files selected</div>';
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <span>📄 ${file.name}</span>
            <button class="remove-btn" onclick="removeFile(${index})">×</button>
        </div>
    `).join('');
}

// Remove File
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
    updateAnalyzeButton();
}

// Add Link
function addLink() {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();

    if (!url) return;

    // Basic validation
    try {
        new URL(url);
    } catch {
        alert('Please enter a valid URL');
        return;
    }

    if (!selectedLinks.includes(url)) {
        selectedLinks.push(url);
        updateLinkList();
        updateAnalyzeButton();
    }

    urlInput.value = '';
}

// Update Link List Display
function updateLinkList() {
    const linkList = document.getElementById('linkList');
    if (selectedLinks.length === 0) {
        linkList.innerHTML = '';
        return;
    }

    linkList.innerHTML = selectedLinks.map((link, index) => `
        <div class="link-item">
            <span>🔗 ${link}</span>
            <button class="remove-btn" onclick="removeLink(${index})">×</button>
        </div>
    `).join('');
}

// Remove Link
function removeLink(index) {
    selectedLinks.splice(index, 1);
    updateLinkList();
    updateAnalyzeButton();
}

// Update Analyze Button State
function updateAnalyzeButton() {
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = selectedFiles.length === 0 && selectedLinks.length === 0;
}


// Start Analysis
async function startAnalysis() {
    const progress = document.getElementById('progress');
    const progressBar = document.getElementById('progressBar');
    const progressCount = document.getElementById('progressCount');
    const progressTotal = document.getElementById('progressTotal');
    const statusList = document.getElementById('statusList');

    progress.classList.remove('hidden');

    const total = selectedFiles.length + selectedLinks.length;
    let completed = 0;

    progressTotal.textContent = total;
    progressCount.textContent = completed;
    statusList.innerHTML = '';

    // Create status items for all files
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        addStatusItem(`file-${i}`, '📄', file.name, 'processing');
    }

    // Create status items for all links
    console.log('Links to process:', selectedLinks);
    for (let i = 0; i < selectedLinks.length; i++) {
        const link = selectedLinks[i];
        addStatusItem(`link-${i}`, '🔗', link, 'processing');
    }

    // Upload files
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const id = `file-${i}`;

        try {
            await uploadFile(file);
            updateStatusItem(id, 'success');
        } catch (error) {
            updateStatusItem(id, 'error');
        }

        completed++;
        progressCount.textContent = completed;
        progressBar.style.width = `${(completed / total) * 100}%`;
    }

    // Upload links
    for (let i = 0; i < selectedLinks.length; i++) {
        const link = selectedLinks[i];
        const id = `link-${i}`;

        try {
            console.log('Uploading link:', link);
            await uploadLink(link);
            updateStatusItem(id, 'success');
        } catch (error) {
            console.error('Link upload error:', error);
            updateStatusItem(id, 'error');
        }

        completed++;
        progressCount.textContent = completed;
        progressBar.style.width = `${(completed / total) * 100}%`;
    }

    // Switch to chat
    setTimeout(() => {
        switchToChat();
    }, 1000);
}

// Add Status Item
function addStatusItem(id, icon, name, state) {
    const statusList = document.getElementById('statusList');
    const item = document.createElement('div');
    item.className = 'status-item';
    item.id = id;
    item.innerHTML = `
        <span class="status-icon">${icon}</span>
        <span class="status-name">${escapeHtml(name)}</span>
        <span class="status-state ${state}">${getStatusText(state)}</span>
    `;
    statusList.appendChild(item);
}

// Update Status Item
function updateStatusItem(id, state) {
    const item = document.getElementById(id);
    if (!item) return;

    const stateEl = item.querySelector('.status-state');
    stateEl.className = `status-state ${state}`;
    stateEl.textContent = getStatusText(state);
}

// Get Status Text
function getStatusText(state) {
    const texts = {
        processing: '⏳ Processing...',
        success: '✓ Done',
        error: '✗ Error'
    };
    return texts[state] || state;
}

// Upload File
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error('Upload failed');
    }

    return await response.json();
}

// Upload Link
async function uploadLink(url) {
    const response = await fetch(`${API_BASE}/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    if (!response.ok) {
        throw new Error('Upload failed');
    }

    return await response.json();
}

// Switch to Chat Screen
function switchToChat() {
    document.getElementById('prepareScreen').classList.remove('active');
    document.getElementById('chatScreen').classList.add('active');
}

// Back to Prepare Screen
function backToPrepare() {
    document.getElementById('chatScreen').classList.remove('active');
    document.getElementById('prepareScreen').classList.add('active');
}

// Send Message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const question = input.value.trim();

    if (!question) return;

    // Add user message
    addMessage('user', question);
    input.value = '';

    // Show loading
    addMessage('assistant', 'Thinking...');

    // Get response
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: question,
                session_id: 'default'
            })
        });

        const data = await response.json();

        // Remove loading message
        const messagesDiv = document.getElementById('messages');
        messagesDiv.removeChild(messagesDiv.lastChild);

        // Add actual response
        addMessage('assistant', data.answer || data.response || 'Sorry, I could not process your question.');
    } catch (error) {
        console.error('Chat error:', error);
        // Remove loading message
        const messagesDiv = document.getElementById('messages');
        messagesDiv.removeChild(messagesDiv.lastChild);
        addMessage('assistant', 'Error: Could not get response. Please try again.');
    }
}

// Add Message to Chat
function addMessage(role, content) {
    messages.push({ role, content });

    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Clear Chat
function clearChat() {
    messages = [];
    document.getElementById('messages').innerHTML = '';
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
updateFileList();
updateLinkList();
updateAnalyzeButton();
