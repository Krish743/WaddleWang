// Basic UI - Replace with proper frontend framework
// API base URL - adjust if backend runs on different port
const API_BASE = 'http://127.0.0.1:8000';

// Parse response as JSON when possible; otherwise return { error: text }
async function parseResponse(response) {
    const text = await response.text();
    if (!text) return {};
    try {
        return JSON.parse(text);
    } catch {
        return { error: text || `Server error (${response.status})` };
    }
}

// Upload form handler
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('uploadStatus');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (!fileInput.files.length) {
        showStatus(statusDiv, 'Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';
    statusDiv.className = 'status';

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await parseResponse(response);

        if (response.ok) {
            showStatus(
                statusDiv,
                `✅ ${data.message} (${data.chunks_ingested} chunks indexed)`,
                'success'
            );
            fileInput.value = '';
        } else {
            const msg = data.detail || data.error || (typeof data.detail === 'string' ? data.detail : 'Upload failed');
            showStatus(statusDiv, `❌ Error: ${msg}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `❌ Network error: ${error.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload & Index';
    }
});

// Ask form handler
document.getElementById('askForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const questionInput = document.getElementById('questionInput');
    const answerDiv = document.getElementById('answer');
    const answerSection = document.getElementById('answerSection');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    const question = questionInput.value.trim();
    if (!question) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Thinking...';
    answerSection.classList.remove('show');
    answerDiv.textContent = '';

    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        const data = await parseResponse(response);

        if (response.ok) {
            answerDiv.textContent = data.answer ?? '';
            answerSection.classList.add('show');
        } else {
            const msg = data.detail || data.error || (typeof data.detail === 'string' ? data.detail : 'Failed to get answer');
            answerDiv.textContent = `Error: ${msg}`;
            answerSection.classList.add('show');
        }
    } catch (error) {
        answerDiv.textContent = `Network error: ${error.message}`;
        answerSection.classList.add('show');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Ask';
    }
});

// Summarize form handler
document.getElementById('summarizeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const sectionInput = document.getElementById('sectionInput');
    const summaryDiv = document.getElementById('summary');
    const summarySection = document.getElementById('summarySection');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    const sectionText = sectionInput.value.trim();
    if (!sectionText) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Summarizing...';
    summarySection.classList.remove('show');
    summaryDiv.textContent = '';

    try {
        const response = await fetch(`${API_BASE}/summarize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ section_text: sectionText }),
        });

        const data = await parseResponse(response);

        if (response.ok) {
            summaryDiv.textContent = data.summary ?? '';
            summarySection.classList.add('show');
        } else {
            const msg = data.detail || data.error || (typeof data.detail === 'string' ? data.detail : 'Failed to summarize');
            summaryDiv.textContent = `Error: ${msg}`;
            summarySection.classList.add('show');
        }
    } catch (error) {
        summaryDiv.textContent = `Network error: ${error.message}`;
        summarySection.classList.add('show');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Summarize';
    }
});

// Helper function
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
}
