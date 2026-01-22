// Simple Upload Interface State
let selectedItems = [];  // Will hold {type: 'file'|'url', data: file|url, name: string}

// Add URL to selected items
function addUrl() {
    const urlInput = document.getElementById('urlInputMain');
    const url = urlInput.value.trim();

    if (!url) {
        showStatus('Please enter a URL', 'error');
        return;
    }

    // Basic URL validation
    try {
        new URL(url);
    } catch (e) {
        showStatus('Please enter a valid URL', 'error');
        return;
    }

    // Add to selected items
    selectedItems.push({
        type: 'url',
        data: url,
        name: url
    });

    urlInput.value = '';
    updateSelectedItemsDisplay();
}

// Update file input handler
const originalFileInput = document.getElementById('fileInput');
if (originalFileInput) {
    originalFileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);

        // Validate and add files
        const supportedExtensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md'];
        const validFiles = files.filter(f => {
            const ext = f.name.toLowerCase().substring(f.name.lastIndexOf('.'));
            return supportedExtensions.includes(ext);
        });

        if (validFiles.length === 0 && files.length > 0) {
            showStatus('Please select supported file types', 'error');
            return;
        }

        // Add valid files to selected items
        validFiles.forEach(file => {
            selectedItems.push({
                type: 'file',
                data: file,
                name: file.name
            });
        });

        updateSelectedItemsDisplay();
    });
}

// Update selected items display
function updateSelectedItemsDisplay() {
    const container = document.getElementById('selectedItemsContainer');
    const list = document.getElementById('selectedItemsList');
    const count = document.getElementById('selectedItemsCount');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const fileCountDisplay = document.getElementById('fileCountDisplay');

    if (!container || !list || !count) return;

    // Update count
    count.textContent = selectedItems.length;

    // Update file count display
    if (fileCountDisplay) {
        const fileCount = selectedItems.filter(item => item.type === 'file').length;
        fileCountDisplay.textContent = fileCount > 0 ? `${fileCount} file(s) selected` : 'No files selected';
    }

    // Show/hide container
    if (selectedItems.length > 0) {
        container.classList.remove('hidden');
        if (analyzeBtn) analyzeBtn.disabled = false;
    } else {
        container.classList.add('hidden');
        if (analyzeBtn) analyzeBtn.disabled = true;
    }

    // Build list
    list.innerHTML = selectedItems.map((item, index) => `
        <div class="selected-item">
            <span class="selected-item-icon">${item.type === 'file' ? '📄' : '🔗'}</span>
            <div class="selected-item-info">
                <div class="selected-item-name">${escapeHtml(item.name)}</div>
                <div class="selected-item-type">${item.type === 'file' ? 'File' : 'URL'}</div>
            </div>
            <button class="selected-item-remove" onclick="removeItem(${index})" title="Remove">×</button>
        </div>
    `).join('');
}

// Remove item
function removeItem(index) {
    selectedItems.splice(index, 1);
    updateSelectedItemsDisplay();
}

// Clear all items
function clearAllItems() {
    selectedItems = [];
    updateSelectedItemsDisplay();

    // Reset file input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
}

// Start analysis
async function startAnalysis() {
    if (selectedItems.length === 0) {
        showStatus('Please add at least one file or URL', 'error');
        return;
    }

    const processingStatus = document.getElementById('processingStatus');
    const processingList = document.getElementById('processingList');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const startChatContainer = document.getElementById('startChatContainer');

    // Show processing status
    if (processingStatus) processingStatus.classList.remove('hidden');
    if (analyzeBtn) analyzeBtn.disabled = true;

    // Process each item
    let successCount = 0;

    for (let i = 0; i < selectedItems.length; i++) {
        const item = selectedItems[i];

        // Add to processing list
        const itemDiv = document.createElement('div');
        itemDiv.className = 'processing-item';
        itemDiv.id = `processing-${i}`;
        itemDiv.innerHTML = `
            <span class="processing-item-name">${escapeHtml(item.name)}</span>
            <span class="processing-item-status">Processing...</span>
        `;
        if (processingList) processingList.appendChild(itemDiv);

        try {
            if (item.type === 'file') {
                await uploadFile(item.data);
            } else {
                await uploadUrl(item.data);
            }

            // Update status
            const statusEl = itemDiv.querySelector('.processing-item-status');
            if (statusEl) {
                statusEl.textContent = '✓ Done';
                statusEl.classList.add('success');
            }
            successCount++;

        } catch (error) {
            console.error('Error processing item:', error);
            const statusEl = itemDiv.querySelector('.processing-item-status');
            if (statusEl) {
                statusEl.textContent = '✗ Failed';
                statusEl.classList.add('error');
            }
        }
    }

    // Show result
    if (successCount > 0) {
        showStatus(`Successfully analyzed ${successCount} of ${selectedItems.length} items`, 'success');

        // Show start chat button
        if (startChatContainer) startChatContainer.classList.remove('hidden');

        // Update hasDocuments state
        hasDocuments = true;
    } else {
        showStatus('Failed to analyze documents', 'error');
        if (analyzeBtn) analyzeBtn.disabled = false;
    }
}

// Upload single file (reuse existing logic)
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
    }

    const result = await response.json();
    await loadDocuments();  // Refresh document list
    return result;
}

// Upload URL (fixed)
async function uploadUrl(url) {
    const response = await fetch(`${API_BASE}/upload-url`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    });

    if (!response.ok) {
        throw new Error(`URL upload failed: ${response.statusText}`);
    }

    const result = await response.json();
    await loadDocuments();  // Refresh document list
    return result;
}

// Helper function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
