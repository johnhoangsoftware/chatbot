// Handle analyze button click for simple form
function handleAnalyzeClick() {
    const fileInput = document.getElementById('fileInput');
    const urlInput = document.getElementById('urlInputMain');

    const files = fileInput.files;
    const url = urlInput.value.trim();

    // Check if user provided any input
    if (files.length === 0 && !url) {
        showStatus('Please select files or enter a URL', 'error');
        return;
    }

    // Process files if selected
    if (files.length > 0) {
        uploadMultipleFiles(Array.from(files));
    }

    // Process URL if provided
    if (url) {
        uploadFromUrl(url);
    }
}

// Update file count display
const fileInputEl = document.getElementById('fileInput');
if (fileInputEl) {
    fileInputEl.addEventListener('change', function (e) {
        const fileCountText = document.getElementById('fileCountText');
        const count = e.target.files.length;

        if (fileCountText) {
            if (count === 0) {
                fileCountText.textContent = 'No files selected';
            } else if (count === 1) {
                fileCountText.textContent = '1 file selected';
            } else {
                fileCountText.textContent = `${count} files selected`;
            }
        }
    });
}

// Upload from URL (wrapper for the main URL input)
function uploadFromUrl(url) {
    if (!url) {
        const urlInput = document.getElementById('urlInputMain');
        url = urlInput ? urlInput.value.trim() : '';
    }

    if (!url) {
        showStatus('Please enter a URL', 'error');
        return;
    }

    // Use existing upload URL functionality
    const urlInputSidebar = document.getElementById('urlInput');
    if (urlInputSidebar) {
        urlInputSidebar.value = url;

        // Trigger the existing uploadFromUrl function if it exists
        if (typeof window.uploadFromUrlOriginal === 'function') {
            window.uploadFromUrlOriginal();
        } else {
            // Call API directly
            fetch(`${API_BASE}/upload-url`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatus('URL processed successfully', 'success');
                        loadDocuments();

                        // Clear input
                        const urlInputMain = document.getElementById('urlInputMain');
                        if (urlInputMain) urlInputMain.value = '';
                    } else {
                        showStatus('Failed to process URL', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showStatus('Error processing URL', 'error');
                });
        }
    }
}
