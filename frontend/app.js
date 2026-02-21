// â”€â”€ PolicyAssist Intelligence System â€“ Frontend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// All API calls go through this single constant.
const API_BASE = 'http://127.0.0.1:8000';

// â”€â”€ Utility helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, options);
    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch { data = { error: text }; }
    return { ok: res.ok, status: res.status, data };
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function setLoading(btn, loading) {
    const label = btn.querySelector('.btn-label');
    const loader = btn.querySelector('.btn-loader');
    btn.disabled = loading;
    if (label && loader) {
        label.classList.toggle('hidden', loading);
        loader.classList.toggle('hidden', !loading);
    }
}

function showResult(el, html, type = 'info') {
    el.innerHTML = html;
    el.className = `result-card ${type}`;
    el.classList.remove('hidden');
}

function hideEl(el) { el.classList.add('hidden'); }
function showEl(el) { el.classList.remove('hidden'); }


// Render source cards into a container element
function renderSources(sources, listEl, wrapEl) {
    if (!sources || sources.length === 0) { hideEl(wrapEl); return; }
    listEl.innerHTML = sources.map(src => `
    <div class="source-card">
      <span class="source-page">Page ${escHtml(src.page)}</span>
      <blockquote class="source-excerpt">${escHtml(src.excerpt)}</blockquote>
    </div>
  `).join('');
    showEl(wrapEl);
}

// â”€â”€ Tab navigation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const tabs = ['upload', 'ask', 'scenario', 'sections'];


document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        tabs.forEach(t => {
            document.getElementById(`tab-${t}`).classList.toggle('active', t === target);
            document.getElementById(`nav-${t}`).classList.toggle('active', t === target);
        });
    });
});

// â”€â”€ API health check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function checkHealth() {
    const dot = document.getElementById('apiStatusDot');
    const text = document.getElementById('apiStatusText');
    try {
        const { ok } = await apiFetch('/health');
        if (ok) {
            dot.classList.add('online'); dot.classList.remove('offline');
            text.textContent = 'API online';
        } else throw new Error();
    } catch {
        dot.classList.add('offline'); dot.classList.remove('online');
        text.textContent = 'API offline';
    }
}
checkHealth();
setInterval(checkHealth, 30_000);

// â”€â”€ 1. UPLOAD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const uploadFilename = document.getElementById('uploadFilename');
const uploadBtn = document.getElementById('uploadBtn');
const uploadResult = document.getElementById('uploadResult');
const uploadStats = document.getElementById('uploadStats');

// Click zone or browse button â†’ open file picker
uploadZone.addEventListener('click', (e) => {
    if (e.target !== browseBtn) fileInput.click();
});
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

// Drag & drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
    uploadFilename.textContent = file.name;
    uploadBtn.disabled = false;
}

uploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    setLoading(uploadBtn, true);
    hideEl(uploadResult);
    hideEl(uploadStats);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const { ok, data } = await apiFetch('/upload', { method: 'POST', body: formData });
        if (ok) {
            showResult(uploadResult,
                `âœ… <strong>${escHtml(data.filename || file.name)}</strong> uploaded and indexed successfully.`,
                'success'
            );
            // Stats chips
            document.querySelector('#statChunks .stat-val').textContent = data.chunks_ingested ?? 'â€”';
            document.querySelector('#statTables .stat-val').textContent = data.tables_ingested ?? 'â€”';
            document.querySelector('#statSections .stat-val').textContent = data.sections_detected ?? 'â€”';
            showEl(uploadStats);
            // Reset
            fileInput.value = '';
            uploadFilename.textContent = '';
            uploadBtn.disabled = true;
        } else {
            showResult(uploadResult, `âŒ ${escHtml(data.detail || data.error || 'Upload failed')}`, 'error');
        }
    } catch (err) {
        showResult(uploadResult, `âŒ Network error: ${escHtml(err.message)}`, 'error');
    } finally {
        setLoading(uploadBtn, false);
    }
});

// â”€â”€ 2. ASK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const askBtn = document.getElementById('askBtn');
const questionInput = document.getElementById('questionInput');
const askResult = document.getElementById('askResult');
const askBadges = document.getElementById('askBadges');
const gapAlert = document.getElementById('gapAlert');
const gapSuggestion = document.getElementById('gapSuggestion');
const answerBox = document.getElementById('answerBox');
const sourcesWrap = document.getElementById('sourcesWrap');
const sourcesList = document.getElementById('sourcesList');

async function handleAsk() {
    const question = questionInput.value.trim();
    if (!question) return;

    setLoading(askBtn, true);
    hideEl(askResult);

    try {
        const { ok, data } = await apiFetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        // Gap alert
        if (data.gap_detected) {
            gapSuggestion.textContent = data.suggestion || '';
            showEl(gapAlert);
        } else {
            hideEl(gapAlert);
        }

        // Answer
        answerBox.textContent = ok
            ? (data.answer || 'No answer returned.')
            : (data.detail || data.error || 'Request failed.');

        // Sources
        renderSources(data.sources, sourcesList, sourcesWrap);

        showEl(askResult);
    } catch (err) {
        answerBox.textContent = `Network error: ${err.message}`;
        hideEl(gapAlert);
        hideEl(sourcesWrap);
        showEl(askResult);
    } finally {
        setLoading(askBtn, false);
    }
}

askBtn.addEventListener('click', handleAsk);
questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleAsk();
});

// â”€â”€ 3. SCENARIO / COMPLIANCE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const scenarioBtn = document.getElementById('scenarioBtn');
const scenarioInput = document.getElementById('scenarioInput');
const scenarioResult = document.getElementById('scenarioResult');
const scenarioBadges = document.getElementById('scenarioBadges');
const scenarioGapAlert = document.getElementById('scenarioGapAlert');
const scenarioGapSuggestion = document.getElementById('scenarioGapSuggestion');
const scenarioOutcome = document.getElementById('scenarioOutcome');
const scenarioSourcesWrap = document.getElementById('scenarioSourcesWrap');
const scenarioSourcesList = document.getElementById('scenarioSourcesList');

async function handleScenario() {
    const scenario = scenarioInput.value.trim();
    if (!scenario) return;

    setLoading(scenarioBtn, true);
    hideEl(scenarioResult);

    try {
        const { ok, data } = await apiFetch('/analyze_scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario }),
        });

        if (data.gap_detected) {
            scenarioGapSuggestion.textContent = data.suggestion || '';
            showEl(scenarioGapAlert);
        } else {
            hideEl(scenarioGapAlert);
        }

        scenarioOutcome.textContent = ok
            ? (data.outcome || 'No outcome returned.')
            : (data.detail || data.error || 'Request failed.');

        renderSources(data.sources, scenarioSourcesList, scenarioSourcesWrap);
        showEl(scenarioResult);
    } catch (err) {
        scenarioOutcome.textContent = `Network error: ${err.message}`;
        hideEl(scenarioGapAlert);
        hideEl(scenarioSourcesWrap);
        showEl(scenarioResult);
    } finally {
        setLoading(scenarioBtn, false);
    }
}


scenarioBtn.addEventListener('click', handleScenario);
scenarioInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleScenario();
});

// â”€â”€ 4. SECTIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const loadSectionsBtn = document.getElementById('loadSectionsBtn');
const sectionsResult = document.getElementById('sectionsResult');
const sectionsList = document.getElementById('sectionsList');
const sectionsEmpty = document.getElementById('sectionsEmpty');

loadSectionsBtn.addEventListener('click', async () => {
    setLoading(loadSectionsBtn, true);
    hideEl(sectionsResult);
    hideEl(sectionsEmpty);

    try {
        const { ok, data } = await apiFetch('/sections');

        if (!ok) {
            sectionsEmpty.querySelector('p').textContent = data.detail || 'Failed to load sections.';
            showEl(sectionsEmpty);
            return;
        }

        if (!Array.isArray(data) || data.length === 0) {
            sectionsEmpty.querySelector('p').textContent = 'No sections found. Upload a document first.';
            showEl(sectionsEmpty);
            return;
        }

        sectionsList.innerHTML = data.map(sec => `
            <div class="section-card">
                <div class="section-card-header">
                    <span class="section-card-name">${escHtml(sec.section_name)}</span>
                    <span class="section-page-range">${escHtml(sec.page_range)}</span>
                </div>
                <p class="section-card-summary">${escHtml(sec.summary)}</p>
            </div>
        `).join('');
        showEl(sectionsResult);
    } catch (err) {
        sectionsEmpty.querySelector('p').textContent = `Network error: ${err.message} `;
        showEl(sectionsEmpty);
    } finally {
        setLoading(loadSectionsBtn, false);
    }
});
