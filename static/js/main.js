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

// Track connection status
let currentConnectionVerified = false;
let currentConnectionDetails = null;

// Link Type Change Handler
function onLinkTypeChange() {
    const linkType = document.getElementById('linkType').value;
    const branchInput = document.getElementById('githubBranchInput');
    const urlInput = document.getElementById('urlInput');
    const credentialsSection = document.getElementById('credentialsSection');
    const githubCreds = document.getElementById('githubCredentials');
    const jiraCreds = document.getElementById('jiraCredentials');
    const confluenceCreds = document.getElementById('confluenceCredentials');

    // Reset connection status
    resetConnectionStatus();

    // Hide all credential inputs
    githubCreds.classList.add('hidden');
    jiraCreds.classList.add('hidden');
    confluenceCreds.classList.add('hidden');

    if (linkType === 'github') {
        branchInput.classList.remove('hidden');
        credentialsSection.classList.remove('hidden');
        githubCreds.classList.remove('hidden');
        urlInput.placeholder = 'Enter GitHub repository URL';
        loadSavedCredentials('github');
    } else if (linkType === 'jira') {
        branchInput.classList.add('hidden');
        credentialsSection.classList.remove('hidden');
        jiraCreds.classList.remove('hidden');
        urlInput.placeholder = 'Enter Jira issue/project URL';
        loadSavedCredentials('jira');
    } else if (linkType === 'confluence') {
        branchInput.classList.add('hidden');
        credentialsSection.classList.remove('hidden');
        confluenceCreds.classList.remove('hidden');
        urlInput.placeholder = 'Enter Confluence page URL';
        loadSavedCredentials('confluence');
    } else {
        branchInput.classList.add('hidden');
        credentialsSection.classList.add('hidden');
        urlInput.placeholder = 'Enter URL';
    }
}

// Reset connection status
function resetConnectionStatus() {
    currentConnectionVerified = false;
    currentConnectionDetails = null;
    document.getElementById('addLinkBtn').disabled = true;
    document.getElementById('linkConnectionStatus').textContent = '';
    document.getElementById('linkConnectionStatus').className = 'inline-status';
    document.getElementById('connectionResult').classList.add('hidden');
    document.getElementById('testIcon').textContent = '🔗';
}

// Load saved credentials from localStorage
function loadSavedCredentials(type) {
    const saved = localStorage.getItem(`credentials_${type}`);
    if (saved) {
        try {
            const creds = JSON.parse(saved);
            if (type === 'github') {
                document.getElementById('githubTokenInput').value = creds.token || '';
            } else if (type === 'jira') {
                document.getElementById('jiraEmailInput').value = creds.email || '';
                document.getElementById('jiraTokenInput').value = creds.token || '';
            } else if (type === 'confluence') {
                document.getElementById('confluenceEmailInput').value = creds.email || '';
                document.getElementById('confluenceTokenInput').value = creds.token || '';
            }
        } catch (e) {
            console.error('Error loading saved credentials:', e);
        }
    }
}

// Save credentials to localStorage
function saveCredentials(type) {
    const shouldSave = document.getElementById('saveCredentials').checked;
    if (!shouldSave) return;

    let creds = {};
    if (type === 'github') {
        creds = { token: document.getElementById('githubTokenInput').value };
    } else if (type === 'jira') {
        creds = {
            email: document.getElementById('jiraEmailInput').value,
            token: document.getElementById('jiraTokenInput').value
        };
    } else if (type === 'confluence') {
        creds = {
            email: document.getElementById('confluenceEmailInput').value,
            token: document.getElementById('confluenceTokenInput').value
        };
    }
    localStorage.setItem(`credentials_${type}`, JSON.stringify(creds));
}

// Add Link - Only works if connection is verified
function addLink() {
    if (!currentConnectionVerified) {
        alert('Please test the connection first');
        return;
    }

    const urlInput = document.getElementById('urlInput');
    const linkTypeSelect = document.getElementById('linkType');
    const branchInput = document.getElementById('githubBranch');

    const url = urlInput.value.trim();
    const linkType = linkTypeSelect.value;
    const branch = branchInput ? branchInput.value.trim() || 'main' : 'main';

    if (!url) return;

    // Basic validation
    try {
        new URL(url);
    } catch {
        alert('Please enter a valid URL');
        return;
    }

    // Create link object with metadata and credentials
    const linkObj = {
        url: url,
        type: linkType,
        branch: linkType === 'github' ? branch : null,
        connectionDetails: currentConnectionDetails
    };

    // Check for duplicates
    if (!selectedLinks.find(l => l.url === url)) {
        selectedLinks.push(linkObj);
        updateLinkList();
        updateAnalyzeButton();
    }

    // Reset for next input
    urlInput.value = '';
    resetConnectionStatus();
}

// Update Link List Display
function updateLinkList() {
    const linkList = document.getElementById('linkList');
    if (selectedLinks.length === 0) {
        linkList.innerHTML = '';
        return;
    }

    linkList.innerHTML = selectedLinks.map((link, index) => {
        const typeIcon = link.type === 'github' ? '📁' :
            link.type === 'jira' ? '🎫' :
                link.type === 'confluence' ? '📄' : '🔗';
        const branchInfo = link.branch ? ` (${link.branch})` : '';
        const displayUrl = link.url.length > 40 ? link.url.substring(0, 40) + '...' : link.url;

        return `
            <div class="link-item">
                <span>${typeIcon} ${displayUrl}${branchInfo}</span>
                <button class="remove-btn" onclick="removeLink(${index})">×</button>
            </div>
        `;
    }).join('');
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
        const displayName = link.branch ? `${link.url} (${link.branch})` : link.url;
        addStatusItem(`link-${i}`, '🔗', displayName, 'processing');
    }

    // Upload files
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const id = `file-${i}`;

        try {
            // Stage 1: Upload
            updateStatusItem(id, 'uploading');
            updateStatusStage(id, 'upload', 'active');
            addStatusLog(id, `Starting upload: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);

            const result = await uploadFile(file);
            updateStatusStage(id, 'upload', 'done');
            addStatusLog(id, `Upload complete`);

            // Stages handled by backend - simulate based on response
            updateStatusStage(id, 'parse', 'done');
            addStatusLog(id, `Parsed successfully`);

            updateStatusStage(id, 'chunk', 'done');
            addStatusLog(id, `Created ${result.chunks_created || 'N/A'} chunks`);

            updateStatusStage(id, 'embed', 'done');
            addStatusLog(id, `Embedded to vector store`);

            updateStatusItem(id, 'success', `Completed: ${result.chunks_created || 0} chunks indexed`);
        } catch (error) {
            updateStatusStage(id, 'upload', 'error');
            updateStatusItem(id, 'error', `Error: ${error.message}`);
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
            // Stage 1: Upload/Fetch
            updateStatusItem(id, 'uploading');
            updateStatusStage(id, 'upload', 'active');
            addStatusLog(id, `Fetching: ${link.url}`);

            console.log('Uploading link:', link);
            const result = await uploadLink(link);
            updateStatusStage(id, 'upload', 'done');
            addStatusLog(id, `Fetched successfully`);

            // Stages handled by backend
            updateStatusStage(id, 'parse', 'done');
            addStatusLog(id, `Parsed content`);

            updateStatusStage(id, 'chunk', 'done');
            addStatusLog(id, `Created ${result.chunks_created || 'N/A'} chunks`);

            updateStatusStage(id, 'embed', 'done');
            addStatusLog(id, `Embedded to vector store`);

            updateStatusItem(id, 'success', `Completed: ${result.chunks_created || 0} chunks indexed`);
        } catch (error) {
            console.error('Link upload error:', error);
            updateStatusStage(id, 'upload', 'error');
            updateStatusItem(id, 'error', `Error: ${error.message}`);
        }

        completed++;
        progressCount.textContent = completed;
        progressBar.style.width = `${(completed / total) * 100}%`;
    }

    // Switch to chat
    // setTimeout(() => {
    //     switchToChat();
    // }, 1000);
}

// Add Status Item with detailed stages
function addStatusItem(id, icon, name, state) {
    const statusList = document.getElementById('statusList');
    const item = document.createElement('div');
    item.className = 'status-item';
    item.id = id;
    item.innerHTML = `
        <div class="status-main">
            <span class="status-icon">${icon}</span>
            <span class="status-name">${escapeHtml(name)}</span>
            <span class="status-state ${state}">${getStatusText(state)}</span>
        </div>
        <div class="status-details hidden">
            <div class="status-stages">
                <span class="stage" data-stage="upload">📤 Upload</span>
                <span class="stage" data-stage="parse">📖 Parse</span>
                <span class="stage" data-stage="chunk">✂️ Chunk</span>
                <span class="stage" data-stage="embed">🧠 Embed</span>
            </div>
            <div class="status-log"></div>
        </div>
    `;
    statusList.appendChild(item);
}

// Update Status Item
function updateStatusItem(id, state, message = null) {
    const item = document.getElementById(id);
    if (!item) return;

    const stateEl = item.querySelector('.status-state');
    stateEl.className = `status-state ${state}`;
    stateEl.textContent = getStatusText(state);

    // Show details when processing
    const details = item.querySelector('.status-details');
    if (state === 'processing' || state === 'success' || state === 'error') {
        details.classList.remove('hidden');
    }

    if (message) {
        addStatusLog(id, message, state === 'error' ? 'error' : 'info');
    }
}

// Update specific stage in status item
function updateStatusStage(id, stage, status) {
    const item = document.getElementById(id);
    if (!item) return;

    const stageEl = item.querySelector(`.stage[data-stage="${stage}"]`);
    if (stageEl) {
        stageEl.classList.remove('pending', 'active', 'done', 'error');
        stageEl.classList.add(status);
    }
}

// Add log message to status item
function addStatusLog(id, message, type = 'info') {
    const item = document.getElementById(id);
    if (!item) return;

    const logEl = item.querySelector('.status-log');
    const time = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.innerHTML = `<span class="log-time">[${time}]</span> ${escapeHtml(message)}`;
    logEl.appendChild(logEntry);
    logEl.scrollTop = logEl.scrollHeight;
}

// Get Status Text
function getStatusText(state) {
    const texts = {
        pending: '⏸️ Pending',
        uploading: '📤 Uploading...',
        parsing: '📖 Parsing...',
        chunking: '✂️ Chunking...',
        embedding: '🧠 Embedding...',
        processing: '⏳ Processing...',
        success: '✅ Done',
        error: '❌ Error'
    };
    return texts[state] || state;
}

// Upload File
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    // Add chunking settings
    formData.append('strategy', document.getElementById('chunkStrategy')?.value || 'structure');
    formData.append('chunk_size', document.getElementById('chunkSize')?.value || '1000');
    formData.append('chunk_overlap', document.getElementById('chunkOverlap')?.value || '200');

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
async function uploadLink(linkObj) {
    // linkObj = { url, type, branch, connectionDetails }
    // connectionDetails may contain: github_token, email, api_token

    const credentials = linkObj.connectionDetails || {};

    const response = await fetch(`${API_BASE}/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            url: linkObj.url,
            link_type: linkObj.type || 'auto',
            branch: linkObj.branch || 'main',
            strategy: document.getElementById('chunkStrategy')?.value || 'structure',
            chunk_size: parseInt(document.getElementById('chunkSize')?.value || '1000'),
            chunk_overlap: parseInt(document.getElementById('chunkOverlap')?.value || '200'),
            // Credentials - single token field
            email: credentials.email || null,
            token: credentials.token || null
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Upload failed');
    }

    return await response.json();
}

// Switch to Chat Screen
function switchToChat() {
    // document.getElementById('prepareScreen').classList.remove('active');
    window.location.href = "http://localhost:3000/";
    // document.getElementById('chatScreen').classList.add('active');
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

// Extract base URL from Atlassian link (e.g., https://domain.atlassian.net/browse/XXX -> https://domain.atlassian.net)
function extractBaseUrl(url) {
    try {
        const urlObj = new URL(url);
        return `${urlObj.protocol}//${urlObj.host}`;
    } catch {
        return url;
    }
}

// Reset testing state when validation fails
function resetTestingState() {
    const statusSpan = document.getElementById('linkConnectionStatus');
    const testIcon = document.getElementById('testIcon');
    statusSpan.textContent = '';
    statusSpan.className = 'inline-status';
    testIcon.textContent = '🔗';
}

// Toggle chunk size settings visibility based on strategy
function toggleChunkSizeSettings() {
    const strategy = document.getElementById('chunkStrategy').value;
    const sizeSettings = document.getElementById('chunkSizeSettings');

    if (strategy === 'fast') {
        sizeSettings.classList.remove('hidden');
    } else {
        sizeSettings.classList.add('hidden');
    }
}

// ========================================
// Inline Connection Testing
// ========================================

// Test current connection based on link type
async function testCurrentConnection() {
    const linkType = document.getElementById('linkType').value;
    const url = document.getElementById('urlInput').value.trim();
    const statusSpan = document.getElementById('linkConnectionStatus');
    const resultDiv = document.getElementById('connectionResult');
    const testIcon = document.getElementById('testIcon');
    const addBtn = document.getElementById('addLinkBtn');

    // Detect type if auto
    let detectedType = linkType;
    if (linkType === 'auto') {
        if (url.includes('github.com')) {
            detectedType = 'github';
        } else if (url.includes('atlassian.net') && url.includes('jira')) {
            detectedType = 'jira';
        } else if (url.includes('atlassian.net') && (url.includes('wiki') || url.includes('confluence'))) {
            detectedType = 'confluence';
        } else {
            // For regular URLs, allow without test
            currentConnectionVerified = true;
            addBtn.disabled = false;
            statusSpan.textContent = '✓ Ready';
            statusSpan.className = 'inline-status connected';
            return;
        }
    }

    if (!url) {
        showInlineResult(false, 'Please enter a URL first');
        return;
    }

    // Show testing state
    statusSpan.textContent = 'Testing...';
    statusSpan.className = 'inline-status testing';
    testIcon.textContent = '⏳';
    resultDiv.classList.add('hidden');
    addBtn.disabled = true;

    try {
        let response;
        let requestBody;

        if (detectedType === 'github') {
            const token = document.getElementById('githubTokenInput')?.value || '';
            requestBody = {
                repo_url: url,
                github_token: token || null
            };
            response = await fetch(`${API_BASE}/test-github-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
        } else if (detectedType === 'jira') {
            // Extract base URL from link (e.g., https://domain.atlassian.net/browse/ISSUE-123)
            const jiraBaseUrl = extractBaseUrl(url);
            const email = document.getElementById('jiraEmailInput')?.value || '';
            const token = document.getElementById('jiraTokenInput')?.value || '';

            if (!email || !token) {
                showInlineResult(false, 'Please fill in Email and API Token for Jira');
                resetTestingState();
                return;
            }

            requestBody = {
                jira_url: jiraBaseUrl,
                email: email,
                api_token: token
            };
            response = await fetch(`${API_BASE}/test-jira-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
        } else if (detectedType === 'confluence') {
            // Extract base URL from link (e.g., https://domain.atlassian.net/wiki/spaces/...)
            let confBaseUrl = extractBaseUrl(url);
            // Include /wiki if not already
            if (!confBaseUrl.includes('/wiki')) {
                confBaseUrl = confBaseUrl + '/wiki';
            }
            const email = document.getElementById('confluenceEmailInput')?.value || '';
            const token = document.getElementById('confluenceTokenInput')?.value || '';

            if (!email || !token) {
                showInlineResult(false, 'Please fill in Email and API Token for Confluence');
                resetTestingState();
                return;
            }

            requestBody = {
                confluence_url: confBaseUrl,
                email: email,
                api_token: token
            };
            response = await fetch(`${API_BASE}/test-confluence-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
        }

        const data = await response.json();

        if (data.success) {
            currentConnectionVerified = true;

            // Store actual credentials from input fields (not just backend response)
            if (detectedType === 'github') {
                currentConnectionDetails = {
                    type: 'github',
                    token: document.getElementById('githubTokenInput')?.value || null
                };
            } else if (detectedType === 'jira') {
                currentConnectionDetails = {
                    type: 'jira',
                    email: document.getElementById('jiraEmailInput')?.value || null,
                    token: document.getElementById('jiraTokenInput')?.value || null
                };
            } else if (detectedType === 'confluence') {
                currentConnectionDetails = {
                    type: 'confluence',
                    email: document.getElementById('confluenceEmailInput')?.value || null,
                    token: document.getElementById('confluenceTokenInput')?.value || null
                };
            }

            statusSpan.textContent = '✓ Connected';
            statusSpan.className = 'inline-status connected';
            testIcon.textContent = '✅';
            addBtn.disabled = false;
            showInlineResult(true, data.message, data.details);

            // Save credentials if checkbox is checked
            saveCredentials(detectedType);
        } else {
            currentConnectionVerified = false;
            statusSpan.textContent = '✗ Failed';
            statusSpan.className = 'inline-status error';
            testIcon.textContent = '❌';
            addBtn.disabled = true;
            showInlineResult(false, data.message, data.details);
        }
    } catch (error) {
        currentConnectionVerified = false;
        statusSpan.textContent = '✗ Error';
        statusSpan.className = 'inline-status error';
        testIcon.textContent = '❌';
        addBtn.disabled = true;
        showInlineResult(false, `Connection error: ${error.message}`);
    }
}

// Show inline connection result
function showInlineResult(success, message, details = null) {
    const resultDiv = document.getElementById('connectionResult');
    resultDiv.classList.remove('hidden', 'success', 'error');
    resultDiv.classList.add(success ? 'success' : 'error');

    let detailsHtml = '';
    if (details && success) {
        detailsHtml = '<div class="result-info">';
        const importantKeys = ['repo_name', 'display_name', 'default_branch', 'stars', 'language'];
        for (const key of importantKeys) {
            if (details[key] !== undefined && details[key] !== null) {
                const formattedKey = key.replace(/_/g, ' ');
                detailsHtml += `<span class="info-tag">${formattedKey}: ${details[key]}</span>`;
            }
        }
        detailsHtml += '</div>';
    }

    resultDiv.innerHTML = `
        <div><strong>${success ? '✅' : '❌'}</strong> ${message}</div>
        ${detailsHtml}
    `;
}

// Initialize
updateFileList();
updateLinkList();
updateAnalyzeButton();

// Toggle Settings Panel
function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    const arrow = document.getElementById('settingsArrow');
    panel.classList.toggle('hidden');
    arrow.classList.toggle('open');
}

// Toggle Integration Settings
function toggleIntegrationSettings() {
    const panel = document.getElementById('integrationPanel');
    const arrow = document.getElementById('integrationArrow');
    panel.classList.toggle('hidden');
    arrow.classList.toggle('open');
}

// ========================================
// Connection Testing Functions
// ========================================

// Test GitHub Connection
async function testGitHubConnection() {
    const repoUrl = document.getElementById('githubRepoUrl').value.trim();
    const token = document.getElementById('githubToken').value.trim();
    const statusBadge = document.getElementById('githubStatus');
    const resultDiv = document.getElementById('githubResult');
    const testIcon = document.getElementById('githubTestIcon');

    if (!repoUrl) {
        showConnectionResult('github', false, 'Please enter a GitHub repository URL');
        return;
    }

    // Show loading state
    statusBadge.textContent = 'Testing...';
    statusBadge.className = 'status-badge loading';
    testIcon.textContent = '⏳';
    resultDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/test-github-connection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                repo_url: repoUrl,
                github_token: token || null
            })
        });

        const data = await response.json();

        if (data.success) {
            statusBadge.textContent = 'Connected';
            statusBadge.className = 'status-badge connected';
            testIcon.textContent = '✅';
            showConnectionResult('github', true, data.message, data.details);
        } else {
            statusBadge.textContent = 'Failed';
            statusBadge.className = 'status-badge error';
            testIcon.textContent = '❌';
            showConnectionResult('github', false, data.message, data.details);
        }
    } catch (error) {
        statusBadge.textContent = 'Error';
        statusBadge.className = 'status-badge error';
        testIcon.textContent = '❌';
        showConnectionResult('github', false, `Connection error: ${error.message}`);
    }
}

// Test Jira Connection
async function testJiraConnection() {
    const jiraUrl = document.getElementById('jiraUrl').value.trim();
    const email = document.getElementById('jiraEmail').value.trim();
    const apiToken = document.getElementById('jiraApiToken').value.trim();
    const statusBadge = document.getElementById('jiraStatus');
    const resultDiv = document.getElementById('jiraResult');
    const testIcon = document.getElementById('jiraTestIcon');

    if (!jiraUrl || !email || !apiToken) {
        showConnectionResult('jira', false, 'Please fill in all Jira credentials');
        return;
    }

    // Show loading state
    statusBadge.textContent = 'Testing...';
    statusBadge.className = 'status-badge loading';
    testIcon.textContent = '⏳';
    resultDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/test-jira-connection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jira_url: jiraUrl,
                email: email,
                api_token: apiToken
            })
        });

        const data = await response.json();

        if (data.success) {
            statusBadge.textContent = 'Connected';
            statusBadge.className = 'status-badge connected';
            testIcon.textContent = '✅';
            showConnectionResult('jira', true, data.message, data.details);
        } else {
            statusBadge.textContent = 'Failed';
            statusBadge.className = 'status-badge error';
            testIcon.textContent = '❌';
            showConnectionResult('jira', false, data.message, data.details);
        }
    } catch (error) {
        statusBadge.textContent = 'Error';
        statusBadge.className = 'status-badge error';
        testIcon.textContent = '❌';
        showConnectionResult('jira', false, `Connection error: ${error.message}`);
    }
}

// Test Confluence Connection
async function testConfluenceConnection() {
    const confluenceUrl = document.getElementById('confluenceUrl').value.trim();
    const email = document.getElementById('confluenceEmail').value.trim();
    const apiToken = document.getElementById('confluenceApiToken').value.trim();
    const statusBadge = document.getElementById('confluenceStatus');
    const resultDiv = document.getElementById('confluenceResult');
    const testIcon = document.getElementById('confluenceTestIcon');

    if (!confluenceUrl || !email || !apiToken) {
        showConnectionResult('confluence', false, 'Please fill in all Confluence credentials');
        return;
    }

    // Show loading state
    statusBadge.textContent = 'Testing...';
    statusBadge.className = 'status-badge loading';
    testIcon.textContent = '⏳';
    resultDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/test-confluence-connection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                confluence_url: confluenceUrl,
                email: email,
                api_token: apiToken
            })
        });

        const data = await response.json();

        if (data.success) {
            statusBadge.textContent = 'Connected';
            statusBadge.className = 'status-badge connected';
            testIcon.textContent = '✅';
            showConnectionResult('confluence', true, data.message, data.details);
        } else {
            statusBadge.textContent = 'Failed';
            statusBadge.className = 'status-badge error';
            testIcon.textContent = '❌';
            showConnectionResult('confluence', false, data.message, data.details);
        }
    } catch (error) {
        statusBadge.textContent = 'Error';
        statusBadge.className = 'status-badge error';
        testIcon.textContent = '❌';
        showConnectionResult('confluence', false, `Connection error: ${error.message}`);
    }
}

// Show Connection Result
function showConnectionResult(type, success, message, details = null) {
    const resultDiv = document.getElementById(`${type}Result`);
    resultDiv.classList.remove('hidden', 'success', 'error');
    resultDiv.classList.add(success ? 'success' : 'error');

    let detailsHtml = '';
    if (details && success) {
        detailsHtml = '<ul class="result-details">';
        for (const [key, value] of Object.entries(details)) {
            if (value !== null && value !== undefined) {
                const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                detailsHtml += `<li>• ${formattedKey}: ${value}</li>`;
            }
        }
        detailsHtml += '</ul>';
    }

    resultDiv.innerHTML = `
        <div class="result-title">${success ? '✅ Success' : '❌ Failed'}</div>
        <div>${message}</div>
        ${detailsHtml}
    `;
}
