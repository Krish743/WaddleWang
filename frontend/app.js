// ── PolicyAssist Intelligence System – Frontend ─────────────
// All API calls go through this single constant.
const API_BASE = 'http://127.0.0.1:8000';

// ── Utility helpers ───────────────────────────────────────────

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

// Confidence badge colour
function confidenceBadgeClass(conf) {
    if (!conf) return 'badge-type';
    const c = conf.toLowerCase();
    if (c === 'high') return 'badge-high';
    if (c === 'medium') return 'badge-medium';
    return 'badge-low';
}

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

// ── Tab navigation ────────────────────────────────────────────

const tabs = ['upload', 'ask', 'scenario', 'sections', 'compare'];

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        tabs.forEach(t => {
            document.getElementById(`tab-${t}`).classList.toggle('active', t === target);
            document.getElementById(`nav-${t}`).classList.toggle('active', t === target);
        });
    });
});

// ── API health check ──────────────────────────────────────────

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

// ── 1. UPLOAD ─────────────────────────────────────────────────

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const uploadFilename = document.getElementById('uploadFilename');
const uploadBtn = document.getElementById('uploadBtn');
const uploadResult = document.getElementById('uploadResult');
const uploadStats = document.getElementById('uploadStats');

// Click zone or browse button → open file picker
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
                `✅ <strong>${escHtml(data.filename || file.name)}</strong> uploaded and indexed successfully.`,
                'success'
            );
            // Stats chips
            document.querySelector('#statChunks .stat-val').textContent = data.chunks_ingested ?? '—';
            document.querySelector('#statTables .stat-val').textContent = data.tables_ingested ?? '—';
            document.querySelector('#statSections .stat-val').textContent = data.sections_detected ?? '—';
            showEl(uploadStats);
            // Reset
            fileInput.value = '';
            uploadFilename.textContent = '';
            uploadBtn.disabled = true;
        } else {
            showResult(uploadResult, `❌ ${escHtml(data.detail || data.error || 'Upload failed')}`, 'error');
        }
    } catch (err) {
        showResult(uploadResult, `❌ Network error: ${escHtml(err.message)}`, 'error');
    } finally {
        setLoading(uploadBtn, false);
    }
});

// ── 2. ASK ────────────────────────────────────────────────────

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

        // Badges
        const confClass = confidenceBadgeClass(data.confidence);
        const typeLabel = (data.query_type || 'factual_lookup').replace(/_/g, ' ');
        askBadges.innerHTML = `
      <span class="badge badge-type">🔍 ${escHtml(typeLabel)}</span>
      <span class="badge ${confClass}">◉ ${escHtml(data.confidence || 'Unknown')} confidence</span>
    `;

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
        askBadges.innerHTML = '';
        showEl(askResult);
    } finally {
        setLoading(askBtn, false);
    }
}

askBtn.addEventListener('click', handleAsk);
questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleAsk();
});

// ── 3. SCENARIO / COMPLIANCE ──────────────────────────────────

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

        const confClass = confidenceBadgeClass(data.confidence);
        scenarioBadges.innerHTML = `
      <span class="badge badge-type">⚖ Compliance Analysis</span>
      <span class="badge ${confClass}">◉ ${escHtml(data.confidence || 'Unknown')} confidence</span>
    `;

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
        scenarioBadges.innerHTML = '';
        showEl(scenarioResult);
    } finally {
        setLoading(scenarioBtn, false);
    }
}

scenarioBtn.addEventListener('click', handleScenario);
scenarioInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleScenario();
});

// ── 4. SECTIONS ───────────────────────────────────────────────

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
          <span class="section-page-range">Pages ${escHtml(sec.page_range)}</span>
        </div>
        <p class="section-card-summary">${escHtml(sec.summary)}</p>
      </div>
    `).join('');
        showEl(sectionsResult);
    } catch (err) {
        sectionsEmpty.querySelector('p').textContent = `Network error: ${err.message}`;
        showEl(sectionsEmpty);
    } finally {
        setLoading(loadSectionsBtn, false);
    }
});

// ── 5. COMPARE DOCUMENTS ──────────────────────────────────────

const compareBtn = document.getElementById('compareBtn');
const compareZoneA = document.getElementById('compareZoneA');
const compareZoneB = document.getElementById('compareZoneB');
const compareFileA = document.getElementById('compareFileA');
const compareFileB = document.getElementById('compareFileB');
const browseCmpA = document.getElementById('browseCmpA');
const browseCmpB = document.getElementById('browseCmpB');
const compareNameA = document.getElementById('compareNameA');
const compareNameB = document.getElementById('compareNameB');
const compareStatusA = document.getElementById('compareStatusA');
const compareStatusB = document.getElementById('compareStatusB');
const compareResult = document.getElementById('compareResult');
const compareEmpty = document.getElementById('compareEmpty');
const compareEmptyMsg = document.getElementById('compareEmptyMsg');
const diffSummary = document.getElementById('diffSummary');
const diffAdded = document.getElementById('diffAdded');
const diffRemoved = document.getElementById('diffRemoved');

// Wire up file pickers + drag-drop for both zones
function makeCompareZone(zone, input, browseBtn) {
    zone.addEventListener('click', (e) => { if (e.target !== browseBtn) input.click(); });
    browseBtn.addEventListener('click', (e) => { e.stopPropagation(); input.click(); });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) {
            // DataTransfer is read-only – trigger change manually
            const dt = new DataTransfer();
            dt.items.add(e.dataTransfer.files[0]);
            input.files = dt.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

makeCompareZone(compareZoneA, compareFileA, browseCmpA);
makeCompareZone(compareZoneB, compareFileB, browseCmpB);

function refreshCompareBtn() {
    compareBtn.disabled = !(compareFileA.files[0] && compareFileB.files[0]);
}

compareFileA.addEventListener('change', () => {
    compareNameA.textContent = compareFileA.files[0]?.name || '';
    compareStatusA.textContent = '';
    compareStatusA.className = 'compare-upload-status';
    refreshCompareBtn();
});

compareFileB.addEventListener('change', () => {
    compareNameB.textContent = compareFileB.files[0]?.name || '';
    compareStatusB.textContent = '';
    compareStatusB.className = 'compare-upload-status';
    refreshCompareBtn();
});

// Upload a file into an ISOLATED compare collection and return the collection name
async function uploadCmpFile(file, statusEl) {
    statusEl.textContent = 'Uploading…';
    statusEl.className = 'compare-upload-status';
    // Each compare upload goes to its own Chroma collection
    const collectionName = 'compare_' + crypto.randomUUID().replace(/-/g, '');
    const fd = new FormData();
    fd.append('file', file);
    try {
        const { ok, data } = await apiFetch(
            `/upload?collection_name=${encodeURIComponent(collectionName)}`,
            { method: 'POST', body: fd }
        );
        if (ok) {
            statusEl.textContent = '✓ Indexed';
            statusEl.className = 'compare-upload-status ok';
            return collectionName;   // the isolated Chroma collection name
        }
        statusEl.textContent = '✗ ' + (data.detail || 'Upload failed');
        statusEl.className = 'compare-upload-status err';
        return null;
    } catch (err) {
        statusEl.textContent = '✗ Network error';
        statusEl.className = 'compare-upload-status err';
        return null;
    }
}

compareBtn.addEventListener('click', async () => {
    const fileA = compareFileA.files[0];
    const fileB = compareFileB.files[0];
    if (!fileA || !fileB) return;

    setLoading(compareBtn, true);
    hideEl(compareResult);
    hideEl(compareEmpty);

    try {
        // Upload both files sequentially so status labels update visibly
        const collA = await uploadCmpFile(fileA, compareStatusA);
        if (!collA) { compareEmptyMsg.textContent = 'Failed to upload Document A.'; showEl(compareEmpty); return; }

        const collB = await uploadCmpFile(fileB, compareStatusB);
        if (!collB) { compareEmptyMsg.textContent = 'Failed to upload Document B.'; showEl(compareEmpty); return; }

        // Run semantic diff via /compare_documents using isolated collections
        const { ok, data } = await apiFetch('/compare_documents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collection_a: collA, collection_b: collB }),
        });

        if (!ok) {
            compareEmptyMsg.textContent = data.detail || data.error || 'Comparison failed.';
            showEl(compareEmpty);
            return;
        }

        diffSummary.textContent = data.summary || '';

        diffAdded.innerHTML = (data.added_in_b?.length > 0)
            ? data.added_in_b.map(c => `
                <div class="diff-chunk">
                    <div class="diff-chunk-page">Page ${escHtml(c.page)}</div>
                    <div>${escHtml(c.excerpt)}</div>
                </div>`).join('')
            : '<p class="diff-none">No new content detected.</p>';

        diffRemoved.innerHTML = (data.removed_in_b?.length > 0)
            ? data.removed_in_b.map(c => `
                <div class="diff-chunk">
                    <div class="diff-chunk-page">Page ${escHtml(c.page)}</div>
                    <div>${escHtml(c.excerpt)}</div>
                </div>`).join('')
            : '<p class="diff-none">No removed content detected.</p>';

        showEl(compareResult);
    } catch (err) {
        compareEmptyMsg.textContent = `Network error: ${err.message}`;
        showEl(compareEmpty);
    } finally {
        setLoading(compareBtn, false);
    }
});

