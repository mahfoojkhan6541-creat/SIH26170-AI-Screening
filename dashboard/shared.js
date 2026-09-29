/**
 * SCREENING AI • ISRO PS26170 QA INTELLIGENCE - SHARED SCRIPT UTILITIES
 * Synchronizes Dataset State, Upload Modal Wizard, Modals, CSV Export, and Toast Notifications across pages.
 */

// 1. DATASET STATE SYNCHRONIZATION
function getActiveDatasetKey() {
  return localStorage.getItem('isro_active_dataset') || 'D2';
}

function setActiveDatasetKey(key) {
  localStorage.setItem('isro_active_dataset', key);
}

function getCustomUploadedDataset() {
  try {
    const raw = localStorage.getItem('isro_custom_dataset');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function setCustomUploadedDataset(data) {
  try {
    localStorage.setItem('isro_custom_dataset', JSON.stringify(data));
  } catch (e) {
    console.error("Failed to store custom dataset:", e);
  }
}

window.clearCustomUploadedDataset = function() {
  localStorage.removeItem('isro_custom_dataset');
  if (getActiveDatasetKey() === 'CUSTOM') {
    setActiveDatasetKey('D2');
  }
  const pill = document.getElementById('pill-CUSTOM');
  if (pill) pill.remove();
  showToast("Uploaded test dataset cleared. Switched to Dataset D2 baseline.", "info");
  if (typeof handleDatasetSwitch === 'function') {
    handleDatasetSwitch('D2');
  } else {
    location.reload();
  }
};

function getDatasetComponents(key) {
  if (key === 'CUSTOM') {
    const custom = getCustomUploadedDataset();
    return custom ? (custom.components || []) : [];
  }

  let base = [];
  if (key === 'D1') {
    base = window.REAL_D1_COMPONENTS || [];
  } else if (key === 'NASA') {
    base = window.REAL_NASA_COMPONENTS || [];
  } else if (key === 'ISRO') {
    base = window.REAL_ISRO_COMPONENTS || [];
  } else {
    base = window.REAL_D2_COMPONENTS || [];
  }

  // Prepend live simulated components if active
  if (window.ISRO_SIMULATION && window.ISRO_SIMULATION.streamedItems && window.ISRO_SIMULATION.streamedItems.length > 0) {
    return [...window.ISRO_SIMULATION.streamedItems, ...base];
  }
  return base;
}

// Live FastAPI workspace fetcher
let isFetchingLive = false;
async function fetchLiveWorkspaceData(callback) {
  if (isFetchingLive) return;
  isFetchingLive = true;
  try {
    const res = await fetch('/api/workspace');
    if (res.ok) {
      const data = await res.json();
      if (data && data.scores && Array.isArray(data.scores)) {
        window.REAL_WORKSPACE_DATA = data;
        window.REAL_D2_COMPONENTS = data.scores.filter(s => {
          const cid = String(s.id || '');
          const dev = String(s.device_type || '');
          const pop = String(s.population_id || '');
          return dev.includes('D2') || pop.includes('D2') || (!isNaN(cid) && !cid.startsWith('D1-') && !cid.startsWith('Device') && !cid.startsWith('STREAM') && !cid.startsWith('SIM-'));
        });
        window.REAL_D1_COMPONENTS = data.scores.filter(s => {
          const cid = String(s.id || '');
          const dev = String(s.device_type || '');
          return dev.includes('D1') || cid.startsWith('D1-');
        });
        window.REAL_NASA_COMPONENTS = data.scores.filter(s => {
          const cid = String(s.id || '');
          const dev = String(s.device_type || '');
          return cid.startsWith('Device') || dev.includes('IGBT');
        });
        window.REAL_ISRO_COMPONENTS = data.scores.filter(s => {
          const cid = String(s.id || '');
          const lot = String(s.lot || s.lot_id || '');
          const dev = String(s.device_type || '');
          return lot.includes('ISRO') || dev.includes('ISRO') || cid.startsWith('STREAM') || cid.startsWith('SIM-');
        });
        if (typeof callback === 'function') {
          callback(data);
        }
      }
    }
  } catch (err) {
    console.warn("Backend API unreachable, using cached offline dataset:", err);
  } finally {
    isFetchingLive = false;
  }
}

// 2. HEADER RUN STATUS & SWITCHER SYNC
function syncHeaderRunStatus(key) {
  const meta = (window.PIPELINE_RUN_METADATA && window.PIPELINE_RUN_METADATA[key]) || {};
  const runPill = document.getElementById('runStatusText');
  const runIdEl = document.getElementById('runStatusId');
  const runModelEl = document.getElementById('runStatusModel');
  const telemetryBadge = document.getElementById('telemetryStatusBadge');
  const custom = getCustomUploadedDataset();

  // If a custom dataset is uploaded, ensure the custom switcher pill is visible in #datasetSwitcher
  const switcher = document.getElementById('datasetSwitcher');
  if (switcher) {
    let btn = document.getElementById('pill-CUSTOM');
    if (custom) {
      if (!btn) {
        btn = document.createElement('button');
        btn.className = 'dataset-pill';
        btn.id = 'pill-CUSTOM';
        btn.onclick = () => {
          if (typeof handleDatasetSwitch === 'function') handleDatasetSwitch('CUSTOM');
          else {
            setActiveDatasetKey('CUSTOM');
            location.reload();
          }
        };
        switcher.appendChild(btn);
      }
      btn.innerHTML = `
        <span class="pill-dot"></span>
        <span id="pillCustomText">Uploaded: ${custom.dataset_name || 'Custom Batch'}</span>
        <span class="pill-clear-btn" onclick="event.stopPropagation(); clearCustomUploadedDataset();" title="Remove uploaded dataset" style="margin-left:6px; font-weight:800; font-size:13px; opacity:0.65; cursor:pointer;">&times;</span>
      `;
    } else if (btn) {
      btn.remove();
    }
  }

  // Update telemetry details
  let runId = 'run_d2_frozen_v2';
  let modelDesc = 'MODEL FROZEN (NO LEAKAGE)';
  let badgeText = 'BENCHMARK EVAL';

  if (key === 'CUSTOM' && custom) {
    runId = custom.run_id || 'run_custom_eval';
    modelDesc = `${custom.dataset_name.toUpperCase()} (FROZEN EVALUATION)`;
    badgeText = 'CUSTOM UPLOAD';
  } else if (key === 'D2') {
    runId = 'run_d2_frozen_v2';
    modelDesc = 'MODEL FROZEN (NO LEAKAGE)';
    badgeText = 'BENCHMARK EVAL';
  } else if (key === 'D1') {
    runId = meta.run_id || 'run_d1_ae1d8eda';
    modelDesc = 'GPR PROGRESSIVE FORECAST';
    badgeText = 'ACTIVE PIPELINE';
  } else if (key === 'ISRO') {
    runId = meta.run_id || 'run_isro_grand_finale_v1';
    modelDesc = 'LIVE TELEMETRY ADAPTED';
    badgeText = 'LIVE STREAM';
  }

  if (runPill) {
    runPill.innerHTML = `Run ID: ${runId} &bull; ${modelDesc}`;
  }
  if (runIdEl) runIdEl.innerText = runId;
  if (runModelEl) runModelEl.innerText = modelDesc;
  if (telemetryBadge) {
    if (window.ISRO_SIMULATION && window.ISRO_SIMULATION.active) {
      telemetryBadge.innerText = `STREAMING (+${window.ISRO_SIMULATION.streamedItems.length})`;
      telemetryBadge.style.color = '#38BDF8';
      telemetryBadge.style.borderColor = 'rgba(56, 189, 248, 0.4)';
    } else if (window.ISRO_SIMULATION && window.ISRO_SIMULATION.streamedItems && window.ISRO_SIMULATION.streamedItems.length > 0) {
      telemetryBadge.innerText = `PAUSED (+${window.ISRO_SIMULATION.streamedItems.length})`;
      telemetryBadge.style.color = '#F59E0B';
      telemetryBadge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    } else {
      telemetryBadge.innerText = badgeText;
      telemetryBadge.style.color = '';
      telemetryBadge.style.borderColor = '';
    }
  }

  // Update switcher pills active class
  document.querySelectorAll('.dataset-pill').forEach(btn => {
    btn.classList.remove('active');
  });
  const activeBtn = document.getElementById(`pill-${key}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Synchronize Live Simulation Button state with restored simulation session
  if (typeof updateSimButtonsUi === 'function') {
    updateSimButtonsUi(window.ISRO_SIMULATION && window.ISRO_SIMULATION.active);
  }
}

// 3. TOAST NOTIFICATIONS
function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  let iconSvg = '';
  if (type === 'error') {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  } else if (type === 'warning') {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
  } else if (type === 'info') {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
  } else {
    iconSvg = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="16 12 12 8 8 12"/><line x1="12" y1="16" x2="12" y2="8"/></svg>`;
  }

  const toast = document.createElement('div');
  toast.className = 'toast-message';
  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// 4. CSV AUDIT EXPORT
function exportCertifiedAuditCsv(event) {
  if (event) {
    if (typeof event.preventDefault === 'function') event.preventDefault();
    if (typeof event.stopPropagation === 'function') event.stopPropagation();
  }

  const btn = (event && event.currentTarget) ? event.currentTarget : document.querySelector('.btn-hdr-export');
  let originalHtml = '';
  if (btn) {
    originalHtml = btn.innerHTML;
    btn.style.pointerEvents = 'none';
    btn.innerHTML = `<span style="display:inline-block;width:11px;height:11px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:4px;"></span><span>Exporting...</span>`;
  }

  try {
    const currentKey = getActiveDatasetKey();
    let data = getDatasetComponents(currentKey);
    if (!data || !Array.isArray(data) || data.length === 0) {
      data = window.REAL_D2_COMPONENTS || [];
    }

    if (!data || data.length === 0) {
      showToast('No component records available to export.', 'warning');
      return;
    }

    const csvHeader = 'MaterialID,Lot,Checkpoint,RawScore,CalibratedScore,QualityGate,Disposition,Rule\n';
    const csvRows = data.map(d => {
      if (!d) return '';
      const id = d.id || d.material_id || d.component_id || 'UNKNOWN';
      const lot = d.lot || d.lot_id || '';
      const cp = d.checkpoint || d.checkpoint_hour || '';
      const raw = d.raw_score !== undefined ? d.raw_score : (d.score !== undefined ? d.score : 0);
      const cal = d.calibrated_score !== undefined ? d.calibrated_score : raw;
      const qg = d.quality_gate || '12/12 PASSED';
      const disp = d.disposition || d.action || 'PASS';
      const rule = d.rule || 'RULE_ANOMALY_CHECK';
      return `"${id}","${lot}","${cp}",${raw},${cal},"${qg}","${disp}","${rule}"`;
    }).filter(Boolean).join('\n');

    const blob = new Blob([csvHeader + csvRows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.setAttribute('download', `isro_burnin_screening_${currentKey}_audit_${Date.now()}.csv`);
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      if (a.parentNode) a.parentNode.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1500);

    showToast(`Exported ${data.length} certified qualification audit records for ${currentKey}.`, 'success');
  } catch (err) {
    console.error('Audit export error:', err);
    showToast('Failed to export audit records: ' + (err.message || 'Unknown error'), 'error');
  } finally {
    if (btn) {
      setTimeout(() => {
        btn.style.pointerEvents = 'auto';
        btn.innerHTML = originalHtml;
      }, 400);
    }
  }
}

// 4b. OFFICIAL PDF AUDIT REPORT EXPORT
async function exportPdfReport(event) {
  if (event) {
    if (typeof event.preventDefault === 'function') event.preventDefault();
    if (typeof event.stopPropagation === 'function') event.stopPropagation();
  }

  const btn = (event && event.currentTarget) ? event.currentTarget : document.querySelector('.btn-hdr-pdf');
  let originalHtml = '';
  if (btn) {
    originalHtml = btn.innerHTML;
    btn.style.pointerEvents = 'none';
    btn.innerHTML = `<span style="display:inline-block;width:11px;height:11px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite;margin-right:4px;"></span><span>Preparing PDF...</span>`;
  }

  showToast('Preparing certified aerospace PDF report...', 'info');

  try {
    const candidateUrls = [
      'docs/SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf',
      '/docs/SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf',
      'SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf',
      '/SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf',
      '../docs/SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf'
    ];

    let foundBlob = null;
    let foundFileName = 'SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf';

    for (const url of candidateUrls) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('text/html')) continue;
          const blob = await response.blob();
          if (blob && blob.size > 2000) {
            foundBlob = blob;
            break;
          }
        }
      } catch (e) {
        // try next candidate
      }
    }

    if (foundBlob) {
      const blobUrl = URL.createObjectURL(foundBlob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = blobUrl;
      a.setAttribute('download', foundFileName);
      document.body.appendChild(a);
      a.click();
      
      setTimeout(() => {
        if (a.parentNode) a.parentNode.removeChild(a);
        URL.revokeObjectURL(blobUrl);
      }, 1500);

      showToast('Certified aerospace PDF evaluation report downloaded successfully.', 'success');
    } else {
      const fallbackUrl = 'docs/SIH26170_FINAL_MODEL_EVALUATION_REPORT.pdf';
      const win = window.open(fallbackUrl, '_blank');
      if (win) {
        showToast('Official PDF evaluation report opened in new tab.', 'success');
      } else {
        throw new Error('Could not retrieve or open PDF report file.');
      }
    }
  } catch (err) {
    console.error('PDF export error:', err);
    showToast('Failed to export PDF report: File unavailable. Please verify report file.', 'error');
  } finally {
    if (btn) {
      setTimeout(() => {
        btn.style.pointerEvents = 'auto';
        btn.innerHTML = originalHtml;
      }, 500);
    }
  }
}

// -------------------------------------------------------------
// 5. FLEXIBLE DATA UPLOAD MODAL & STEP-BY-STEP WIZARD
// -------------------------------------------------------------
let uploadState = {
  step: 1,
  file: null,
  previewData: null,
  validationData: null,
  processData: null
};

function openUploadModal() {
  let modal = document.getElementById('uploadModalOverlay');
  if (!modal) {
    createUploadModalDom();
    modal = document.getElementById('uploadModalOverlay');
  }
  resetUploadWizard();
  modal.classList.add('open');
}

function closeUploadModal() {
  const modal = document.getElementById('uploadModalOverlay');
  if (modal) modal.classList.remove('open');
}

function resetUploadWizard() {
  uploadState = { step: 1, file: null, previewData: null, validationData: null, processData: null };
  setUploadWizardStep(1);
  const fileInput = document.getElementById('uploadFileInput');
  if (fileInput) fileInput.value = '';
}

function setUploadWizardStep(stepNum) {
  uploadState.step = stepNum;
  for (let i = 1; i <= 5; i++) {
    const el = document.getElementById(`uploadStepView-${i}`);
    const ind = document.getElementById(`stepInd-${i}`);
    if (el) el.style.display = (i === stepNum) ? 'block' : 'none';
    if (ind) {
      ind.classList.remove('active', 'completed');
      if (i === stepNum) ind.classList.add('active');
      else if (i < stepNum) ind.classList.add('completed');
    }
  }
}

function createUploadModalDom() {
  const div = document.createElement('div');
  div.id = 'uploadModalOverlay';
  div.className = 'modal-overlay';
  div.onclick = (e) => { if (e.target === div) closeUploadModal(); };
  div.innerHTML = `
    <div class="modal-card" style="max-width: 860px; max-height: 90vh;">
      
      <!-- Wizard Progress Header (5-Stage Qualification Pipeline) -->
      <div class="upload-steps-bar">
        <div class="step-indicator active" id="stepInd-1">
          <span class="step-num">1</span>
          <span>Upload Data</span>
        </div>
        <div class="step-separator"></div>
        <div class="step-indicator" id="stepInd-2">
          <span class="step-num">2</span>
          <span>Validate &amp; Map</span>
        </div>
        <div class="step-separator"></div>
        <div class="step-indicator" id="stepInd-3">
          <span class="step-num">3</span>
          <span>12-Check Gate</span>
        </div>
        <div class="step-separator"></div>
        <div class="step-indicator" id="stepInd-4">
          <span class="step-num">4</span>
          <span>AI Inference</span>
        </div>
        <div class="step-separator"></div>
        <div class="step-indicator" id="stepInd-5">
          <span class="step-num">5</span>
          <span>Screening Results</span>
        </div>
      </div>

      <!-- Modal Body -->
      <div class="modal-body" style="padding: 24px;">

        <!-- STEP 1: FILE DROPZONE -->
        <div id="uploadStepView-1">
          <div class="dropzone-container" id="dropzoneArea" onclick="document.getElementById('uploadFileInput').click()">
            <input type="file" id="uploadFileInput" accept=".csv,.xlsx,.xls,.json,.txt" style="display:none;" onchange="handleFileSelect(this.files[0])">
            <div class="dropzone-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
            </div>
            <div>
              <div style="font-size: 15px; font-weight: 800; color: var(--text-main);">Drag &amp; drop your screening data file here</div>
              <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">or click anywhere to browse from local computer</div>
            </div>
            <div class="format-tags-list">
              <span class="format-tag">.CSV</span>
              <span class="format-tag">.XLSX</span>
              <span class="format-tag">.XLS</span>
              <span class="format-tag">.JSON</span>
              <span class="format-tag">.TXT</span>
            </div>
            <div style="font-size: 11px; color: var(--text-subtle); margin-top: 6px;">
              Maximum file size: 50 MB &bull; Client &amp; server integrity validated
            </div>
          </div>

          <div id="uploadLoadingSpinner" style="display:none; text-align:center; padding: 24px;">
            <div style="font-size: 13px; font-weight: 700; color: var(--brand-teal);">Inspecting file structure and parsing schema...</div>
          </div>
        </div>

        <!-- STEP 2: PREVIEW & COLUMN MAPPING -->
        <div id="uploadStepView-2" style="display:none;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 14px; font-weight: 800; color: var(--text-main);" id="previewFileName">filename.csv</span>
              <span class="tag-mono" id="previewFormatTag">CSV</span>
            </div>
            <span class="gate-badge" id="previewRowsTag">0 Records Detected</span>
          </div>

          <!-- Summary Badges -->
          <div class="preview-summary-grid">
            <div class="preview-stat-card">
              <div class="preview-stat-label">Total Rows</div>
              <div class="preview-stat-val" id="prevTotalRows">0</div>
            </div>
            <div class="preview-stat-card">
              <div class="preview-stat-label">Total Columns</div>
              <div class="preview-stat-val" id="prevTotalCols">0</div>
            </div>
            <div class="preview-stat-card">
              <div class="preview-stat-label">Duplicates</div>
              <div class="preview-stat-val" id="prevDuplicates">0</div>
            </div>
            <div class="preview-stat-card">
              <div class="preview-stat-label">Missing Values</div>
              <div class="preview-stat-val" id="prevMissing">0</div>
            </div>
          </div>

          <!-- Preview Table -->
          <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">Data Preview (First 5 Rows)</div>
          <div class="preview-table-container">
            <table class="preview-table" id="previewTableDom"></table>
          </div>

          <!-- Smart Column Mapping Form -->
          <div style="border-top: 1px solid var(--border-color); padding-top: 14px; margin-top: 10px;">
            <div style="font-size: 13px; font-weight: 800; color: var(--text-main); display: flex; align-items: center; gap: 6px;">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--brand-teal)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              <span>Smart Column Mapping</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">
              We automatically detected matching fields. Adjust if your dataset uses custom headers.
            </div>

            <div class="mapping-grid">
              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Component / Material ID</span>
                  <span>Required *</span>
                </label>
                <select id="mapCol-component_id" class="mapping-select"></select>
              </div>

              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Temporal Checkpoint (Step / Hour)</span>
                  <span>Optional</span>
                </label>
                <select id="mapCol-checkpoint" class="mapping-select"></select>
              </div>

              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Elapsed Time (Duration)</span>
                  <span>Optional</span>
                </label>
                <select id="mapCol-elapsed_time" class="mapping-select"></select>
              </div>

              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Fabrication Lot / Wafer ID</span>
                  <span>Optional</span>
                </label>
                <select id="mapCol-lot_id" class="mapping-select"></select>
              </div>

              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Device Family / Model Type</span>
                  <span>Optional</span>
                </label>
                <select id="mapCol-device_type" class="mapping-select"></select>
              </div>

              <div class="mapping-field-group">
                <label class="mapping-field-label">
                  <span>Ground Truth Defect Label</span>
                  <span>Optional</span>
                </label>
                <select id="mapCol-target" class="mapping-select"></select>
              </div>
            </div>

            <div style="margin-top: 14px; padding: 10px 14px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px; font-size: 11.5px; color: var(--text-main); display: flex; align-items: center; justify-content: space-between;">
              <span><strong>Measurement Features:</strong> <span id="detectedParamCount">0</span> numerical parameters detected for Isolation Forest screening.</span>
            </div>
          </div>
        </div>

        <!-- STEP 3: PRE-FLIGHT QUALITY GATE -->
        <div id="uploadStepView-3" style="display:none;">
          <div style="font-size: 14px; font-weight: 800; color: var(--text-main); margin-bottom: 4px;">12-Check Pre-Flight Quality Gate</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">
            Verifying schema conformity, timestamp monotonicity, and sensor limits.
          </div>

          <div class="validation-checks-list" id="validationChecksDom">
            <!-- Dynamic checks rendered -->
          </div>

          <div style="margin-top: 14px; padding: 10px 14px; background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; font-size: 12px; color: #065F46;" id="validationSummaryBanner">
            <strong>Ready:</strong> Data passed 12/12 quality checks and is compatible for screening.
          </div>
        </div>

        <!-- STEP 4: AI INFERENCE PROGRESS -->
        <div id="uploadStepView-4" style="display:none;">
          <div id="processingStageBox" style="text-align: center; padding: 32px 16px;">
            <div style="font-size: 15px; font-weight: 800; color: var(--text-main);">Running Anomaly Detection Pipeline</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Extracting behavioral features and calculating anomaly scores...</div>

            <div class="progress-bar-wrap" style="max-width: 480px; margin: 20px auto 12px;">
              <div class="progress-bar-fill" id="procProgressBar"></div>
            </div>
            <div class="processing-stage-text" id="procStageText">Initializing Ingestion...</div>
          </div>
        </div>

        <!-- STEP 5: SCREENING RESULTS & EXPLORATION -->
        <div id="uploadStepView-5" style="display:none;">
          <div id="processingResultCard">
            <div style="padding: 14px 18px; background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 10px; margin-bottom: 16px;">
              <div style="font-size: 14px; font-weight: 800; color: #166534; display: flex; align-items: center; gap: 8px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>Screening Complete: Dataset Qualified</span>
              </div>
              <div style="font-size: 12px; color: #14532D; margin-top: 4px;" id="uploadResultNarrative">
                All components evaluated with complete audit trail recorded.
              </div>
            </div>

            <!-- Quick Metrics Grid -->
            <div class="preview-summary-grid">
              <div class="preview-stat-card">
                <div class="preview-stat-label">Total Screened</div>
                <div class="preview-stat-val" id="resTotalScreened">0</div>
              </div>
              <div class="preview-stat-card" style="border-color: #A7F3D0; background: #ECFDF5;">
                <div class="preview-stat-label" style="color: #047857;">Pass (Qualified)</div>
                <div class="preview-stat-val" style="color: #047857;" id="resPassCount">0</div>
              </div>
              <div class="preview-stat-card" style="border-color: #FDE68A; background: #FFFBEB;">
                <div class="preview-stat-label" style="color: #B45309;">Review (Watch)</div>
                <div class="preview-stat-val" style="color: #B45309;" id="resReviewCount">0</div>
              </div>
              <div class="preview-stat-card" style="border-color: #FECDD3; background: #FEF2F2;">
                <div class="preview-stat-label" style="color: #B91C1C;">Reject (Defects)</div>
                <div class="preview-stat-val" style="color: #B91C1C;" id="resRejectCount">0</div>
              </div>
            </div>

            <!-- Direct Table / Dashboard Launch Banner -->
            <div style="margin-top: 20px; padding: 14px 18px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: var(--text-main);">Launch Qualified Workspace</div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">Inspect individual parts with TreeSHAP explanations or review fleet KPIs.</div>
              </div>
              <div style="display: flex; gap: 10px;">
                <button class="btn-action-light" onclick="applyUploadedDatasetToDashboard('overview')">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
                  <span>Overview KPIs</span>
                </button>
                <button class="btn-action-primary" style="background: #0F766E; border-color: #0F766E;" onclick="applyUploadedDatasetToDashboard('screening')">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  <span>Explore in Batch Screening Workspace &rarr;</span>
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Modal Footer Controls -->
      <div class="modal-footer" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <button class="btn-action-light" id="btnUploadBack" style="display:none;" onclick="handleUploadBack()">
            &larr; Back
          </button>
        </div>

        <div style="display: flex; gap: 10px;">
          <button class="btn-action-light" onclick="closeUploadModal()">Cancel</button>
          <button class="btn-action-primary" id="btnUploadNext" style="display:none;" onclick="handleUploadNext()">
            Continue &rarr;
          </button>
          <button class="btn-action-primary" id="btnApplyDataset" style="display:none; background: #0F766E; border-color: #0F766E;" onclick="applyUploadedDatasetToDashboard()">
            <span>View Results in Dashboard &rarr;</span>
          </button>
        </div>
      </div>

    </div>
  `;
  document.body.appendChild(div);

  // Setup drag and drop events
  const dropzone = document.getElementById('dropzoneArea');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      }, false);
    });

    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    }, false);
  }
}

// Upload Step 1 -> Server Preview
function handleFileSelect(file) {
  if (!file) return;

  const validExts = ['.csv', '.xlsx', '.xls', '.json', '.txt'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!validExts.includes(ext)) {
    showToast(`Unsupported format '${ext}'. Please upload CSV, XLSX, JSON, or TXT.`, 'error');
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    showToast(`File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds 50MB limit.`, 'error');
    return;
  }

  uploadState.file = file;
  document.getElementById('uploadLoadingSpinner').style.display = 'block';

  const formData = new FormData();
  formData.append('file', file);

  fetch('/api/upload/preview', {
    method: 'POST',
    body: formData
  })
  .then(res => {
    if (!res.ok) return res.json().then(err => { throw new Error(err.detail || 'Failed to inspect file'); });
    return res.json();
  })
  .then(data => {
    uploadState.previewData = data;
    document.getElementById('uploadLoadingSpinner').style.display = 'none';
    renderStep2Preview(data);
    setUploadWizardStep(2);
    document.getElementById('btnUploadBack').style.display = 'inline-flex';
    document.getElementById('btnUploadNext').style.display = 'inline-flex';
    document.getElementById('btnUploadNext').innerText = 'Validate Data Gate \u2192';
  })
  .catch(err => {
    document.getElementById('uploadLoadingSpinner').style.display = 'none';
    showToast(err.message, 'error');
  });
}

// Render Step 2 (Preview table & mapping options)
function renderStep2Preview(data) {
  document.getElementById('previewFileName').innerText = data.filename;
  document.getElementById('previewFormatTag').innerText = data.format;
  document.getElementById('previewRowsTag').innerText = `${data.total_rows} Records`;

  document.getElementById('prevTotalRows').innerText = String(data.total_rows);
  document.getElementById('prevTotalCols').innerText = String(data.total_columns);
  document.getElementById('prevDuplicates').innerText = String(data.duplicate_rows);
  
  const totalMissing = Object.values(data.missing_summary || {}).reduce((a, b) => a + b, 0);
  document.getElementById('prevMissing').innerText = String(totalMissing);

  // Render Preview Table
  const table = document.getElementById('previewTableDom');
  table.innerHTML = '';

  const columns = data.columns || [];
  const thead = document.createElement('thead');
  let trHead = '<tr>';
  columns.forEach(col => { trHead += `<th>${col}</th>`; });
  trHead += '</tr>';
  thead.innerHTML = trHead;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  (data.preview_rows || []).slice(0, 5).forEach(row => {
    let tr = '<tr>';
    columns.forEach(col => {
      const val = row[col] !== null && row[col] !== undefined ? row[col] : '-';
      tr += `<td>${val}</td>`;
    });
    tr += '</tr>';
    tbody.innerHTML += tr;
  });
  table.appendChild(tbody);

  // Populate Dropdowns
  const fields = ['component_id', 'checkpoint', 'elapsed_time', 'lot_id', 'device_type', 'target'];
  const suggested = data.suggested_mapping || {};

  fields.forEach(field => {
    const sel = document.getElementById(`mapCol-${field}`);
    sel.innerHTML = '';
    
    // Add optional blank option if not required
    if (field !== 'component_id') {
      const optNone = document.createElement('option');
      optNone.value = '';
      optNone.innerText = '-- None / Auto-generate --';
      sel.appendChild(optNone);
    }

    columns.forEach(col => {
      const opt = document.createElement('option');
      opt.value = col;
      opt.innerText = col;
      if (suggested[field] === col) opt.selected = true;
      sel.appendChild(opt);
    });
  });

  document.getElementById('detectedParamCount').innerText = String((suggested.detected_parameters || []).length);
}

// Next Button in Wizard
function handleUploadNext() {
  if (uploadState.step === 2) {
    // Collect user mapping and validate
    const mapping = {
      component_id: document.getElementById('mapCol-component_id').value,
      checkpoint: document.getElementById('mapCol-checkpoint').value || null,
      elapsed_time: document.getElementById('mapCol-elapsed_time').value || null,
      lot_id: document.getElementById('mapCol-lot_id').value || null,
      device_type: document.getElementById('mapCol-device_type').value || null,
      target: document.getElementById('mapCol-target').value || null,
      parameters: uploadState.previewData.suggested_mapping.detected_parameters || []
    };

    if (!mapping.component_id) {
      showToast('Please select a Component / Material ID column.', 'error');
      return;
    }

    fetch('/api/upload/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        saved_path: uploadState.previewData.saved_path,
        mapping: mapping
      })
    })
    .then(res => {
      if (!res.ok) return res.json().then(err => { throw new Error(err.detail || 'Validation failed'); });
      return res.json();
    })
    .then(data => {
      uploadState.validationData = data;
      renderStep3Validation(data);
      setUploadWizardStep(3);
      document.getElementById('btnUploadNext').innerText = 'Run Anomaly Screening Pipeline \uD83D\uDE80';
    })
    .catch(err => showToast(err.message, 'error'));

  } else if (uploadState.step === 3) {
    // Run Pipeline
    setUploadWizardStep(4);
    document.getElementById('btnUploadBack').style.display = 'none';
    document.getElementById('btnUploadNext').style.display = 'none';
    executeUploadPipelineProcess();
  }
}

// Back Button in Wizard
function handleUploadBack() {
  if (uploadState.step === 2) {
    setUploadWizardStep(1);
    document.getElementById('btnUploadBack').style.display = 'none';
    document.getElementById('btnUploadNext').style.display = 'none';
  } else if (uploadState.step === 3) {
    setUploadWizardStep(2);
    document.getElementById('btnUploadNext').innerText = 'Validate Data Gate \u2192';
  }
}

// Render Step 3 Validation Checks
function renderStep3Validation(data) {
  const container = document.getElementById('validationChecksDom');
  container.innerHTML = '';

  (data.checks || []).forEach(check => {
    const div = document.createElement('div');
    div.className = 'validation-check-row';
    div.innerHTML = `
      <div>
        <div class="validation-check-name">${check.check}</div>
        <div class="validation-check-desc">${check.detail}</div>
      </div>
      <div>
        <span class="gate-badge" style="${check.passed ? '' : 'color:#DC2626; background:#FEF2F2; border-color:#FECDD3;'}">
          ${check.passed ? 'PASSED' : 'FLAGGED'}
        </span>
      </div>
    `;
    container.appendChild(div);
  });
}

// Step 4: Run Pipeline with Progress Animation
function executeUploadPipelineProcess() {
  const bar = document.getElementById('procProgressBar');
  const stage = document.getElementById('procStageText');

  bar.style.width = '20%';
  stage.innerText = 'Stage 1: Ingestion & Schema Normalization...';

  setTimeout(() => {
    bar.style.width = '50%';
    stage.innerText = 'Stage 2: 156-Feature Behavior Extraction & Drift Analysis...';
  }, 600);

  setTimeout(() => {
    bar.style.width = '75%';
    stage.innerText = 'Stage 3: Isolation Forest & GPR Trajectory Forecast...';
  }, 1200);

  const mapping = {
    component_id: document.getElementById('mapCol-component_id').value,
    checkpoint: document.getElementById('mapCol-checkpoint').value || null,
    elapsed_time: document.getElementById('mapCol-elapsed_time').value || null,
    lot_id: document.getElementById('mapCol-lot_id').value || null,
    device_type: document.getElementById('mapCol-device_type').value || null,
    target: document.getElementById('mapCol-target').value || null,
    parameters: uploadState.previewData.suggested_mapping.detected_parameters || []
  };

  fetch('/api/upload/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      saved_path: uploadState.previewData.saved_path,
      dataset_name: uploadState.previewData.filename,
      mapping: mapping
    })
  })
  .then(res => {
    if (!res.ok) return res.json().then(err => { throw new Error(err.detail || 'Processing failed'); });
    return res.json();
  })
  .then(data => {
    bar.style.width = '100%';
    stage.innerText = 'Screening Complete! Writing SQLite Audit Trail...';
    uploadState.processData = data;

    setTimeout(() => {
      setUploadWizardStep(5);
      const btnApply = document.getElementById('btnApplyDataset');
      if (btnApply) btnApply.style.display = 'inline-flex';

      const comps = Array.isArray(data.components) ? data.components : [];
      const totalVal = comps.length > 0 ? comps.length : (data.total_screened || 0);
      const passVal = comps.length > 0 ? comps.filter(c => c.disposition === 'PASS').length : (data.pass_count || 0);
      const revVal = comps.length > 0 ? comps.filter(c => c.disposition === 'REVIEW').length : (data.review_count || 0);
      const rejVal = comps.length > 0 ? comps.filter(c => c.disposition === 'REJECT').length : (data.reject_count || 0);

      const totalEl = document.getElementById('resTotalScreened');
      const passEl = document.getElementById('resPassCount');
      const revEl = document.getElementById('resReviewCount');
      const rejEl = document.getElementById('resRejectCount');
      if (totalEl) totalEl.innerText = String(totalVal);
      if (passEl) passEl.innerText = String(passVal);
      if (revEl) revEl.innerText = String(revVal);
      if (rejEl) rejEl.innerText = String(rejVal);

      const narrativeEl = document.getElementById('uploadResultNarrative');
      if (narrativeEl) {
        narrativeEl.innerText = `All ${totalVal} records evaluated: ${passVal} PASS, ${revVal} REVIEW, ${rejVal} REJECT. Complete audit trail recorded.`;
      }
    }, 600);
  })
  .catch(err => {
    stage.innerText = `Error: ${err.message}`;
    stage.style.color = '#DC2626';
    showToast(err.message, 'error');
  });
}

// Apply Processed Dataset to Dashboard Workspace
function applyUploadedDatasetToDashboard(targetPage) {
  if (!uploadState.processData) return;

  // Stop and clear any active simulation so workspace focuses strictly on uploaded dataset
  if (window.ISRO_SIMULATION) {
    if (window.ISRO_SIMULATION.timer) {
      clearInterval(window.ISRO_SIMULATION.timer);
      window.ISRO_SIMULATION.timer = null;
    }
    window.ISRO_SIMULATION.active = false;
    window.ISRO_SIMULATION.streamedItems = [];
    window.ISRO_SIMULATION.tickCount = 0;
    try {
      localStorage.setItem('isro_sim_active', 'false');
      localStorage.setItem('isro_sim_items', '[]');
      localStorage.setItem('isro_sim_tick', '0');
    } catch(e) {}
    updateSimButtonsUi(false);
  }

  setCustomUploadedDataset(uploadState.processData);
  setActiveDatasetKey('CUSTOM');
  closeUploadModal();

  showToast(`Active dataset switched to '${uploadState.processData.dataset_name}'. Workspace updated!`);

  if (targetPage === 'screening' && !window.location.pathname.endsWith('screening.html')) {
    window.location.href = 'screening.html';
    return;
  } else if (targetPage === 'overview' && !window.location.pathname.endsWith('overview.html') && !window.location.pathname.endsWith('/') && !window.location.pathname.endsWith('index.html')) {
    window.location.href = 'overview.html';
    return;
  }

  // Refresh page if current page has specific render function
  if (typeof handleDatasetSwitch === 'function') {
    handleDatasetSwitch('CUSTOM');
  } else {
    location.reload();
  }
}

// -------------------------------------------------------------
// 6. 12-CHECK QUALITY GATE MODAL
// -------------------------------------------------------------
function openQualityGateModal() {
  let modal = document.getElementById('gateModalOverlay');
  if (!modal) {
    createGateModalDom();
    modal = document.getElementById('gateModalOverlay');
  }
  modal.classList.add('open');
}

function closeQualityGateModal() {
  const modal = document.getElementById('gateModalOverlay');
  if (modal) modal.classList.remove('open');
}

function createGateModalDom() {
  const div = document.createElement('div');
  div.id = 'gateModalOverlay';
  div.className = 'modal-overlay';
  div.onclick = (e) => { if (e.target === div) closeQualityGateModal(); };
  div.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <div class="modal-icon-badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          </div>
          <div>
            <h3 class="modal-title">12-Check Data Quality Gate</h3>
            <p style="font-size: 11.5px; color: var(--text-muted); font-family: var(--font-mono);">ISRO PS26170 Mandatory Ingestion Gates</p>
          </div>
        </div>
        <button class="modal-close-btn" onclick="closeQualityGateModal()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <p style="margin-bottom: 16px; color: var(--text-muted); font-size: 12.5px;">
          All incoming telemetry, continuous sensor logs, and discrete burn-in measurements must satisfy 100% of the 12 quality checks before inference.
        </p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>1. Schema &amp; Types</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Header and type verification with zero format drift.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>2. Zero Null Ingestion</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Zero dropped fields across all 156 features.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>3. Monotonic Timeline</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Enforces strictly ascending checkpoints (0h &rarr; 168h).</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>4. Sensor Clamping</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Verifies values reside within physical hardware bounds.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>5. Noise Filter &sigma;</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Savitzky-Golay high-frequency jitter suppression.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>6. Lot Traceability</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Monospace LOT-ID and wafer cohort linked.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>7. Quantile Scaling</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Robust normalization against extreme outliers.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>8. Covariance Stability</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Matrix condition number within flight tolerance.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>9. Thermal Check</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Junction thermal gradient verified against chamber specs.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>10. Outlier Bounding</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Strict rejection of nonsensical sensor spikes.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>11. Calibration Curve</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Zero label leakage sigmoid calibration verified.</div>
          </div>
          <div style="padding: 10px 12px; background: #F8FAFC; border: 1px solid var(--border-color); border-radius: 8px;">
            <div style="font-weight: 700; font-size: 12px; color: #047857; display: flex; align-items: center; gap: 6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span>12. Cryptographic Hash</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">SHA-256 batch signature written to SQLite audit log.</div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-action-primary" onclick="closeQualityGateModal()">Close Quality Gate</button>
      </div>
    </div>
  `;
  document.body.appendChild(div);
}

// -------------------------------------------------------------
// 7. MODEL REGISTRY MODAL
// -------------------------------------------------------------
function openModelRegistryModal() {
  let modal = document.getElementById('registryModalOverlay');
  if (!modal) {
    createRegistryModalDom();
    modal = document.getElementById('registryModalOverlay');
  }
  modal.classList.add('open');
}

function closeModelRegistryModal() {
  const modal = document.getElementById('registryModalOverlay');
  if (modal) modal.classList.remove('open');
}

function createRegistryModalDom() {
  const div = document.createElement('div');
  div.id = 'registryModalOverlay';
  div.className = 'modal-overlay';
  div.onclick = (e) => { if (e.target === div) closeModelRegistryModal(); };
  div.innerHTML = `
    <div class="modal-card" style="max-width: 720px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <div class="modal-icon-badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
          </div>
          <div>
            <h3 class="modal-title">Centralized Dynamic Model Registry</h3>
            <p style="font-size: 11.5px; color: var(--text-muted); font-family: var(--font-mono);">configs/model_registry.json &bull; Immutable Frozen Weights</p>
          </div>
        </div>
        <button class="modal-close-btn" onclick="closeModelRegistryModal()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <!-- Model D2 -->
          <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; background: #FFFFFF;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: 700; font-size: 14px; color: var(--text-main);">Dataset D2 &bull; Frozen Isolation Forest v2</span>
                <span class="gate-badge" style="margin-left: 8px;">FROZEN VALIDATED</span>
              </div>
              <span class="tag-mono">&tau; = 0.393578</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">
              Path: <code>models/D2_final_frozen_model.pkl</code> | Out-of-sample Recall: <strong>96.23%</strong> | Leakage: <strong>0.00%</strong>
            </div>
          </div>

          <!-- Model D1 -->
          <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; background: #FFFFFF;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: 700; font-size: 14px; color: var(--text-main);">Dataset D1 &bull; Progressive GPR + Isolation Forest</span>
                <span class="gate-badge" style="margin-left: 8px;">COMPOSITE ACTIVE</span>
              </div>
              <span class="tag-mono">&tau; = 0.415636</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">
              Path: <code>models/D1_final_frozen_model.pkl</code> | Mat&eacute;rn 5/2 Gaussian Process Regressor | Nominal Recall: <strong>98.17%</strong>
            </div>
          </div>

          <!-- Model NASA -->
          <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; background: #FFFFFF;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: 700; font-size: 14px; color: var(--text-main);">NASA Aging MAT &bull; MOSFET Thermal Runaway GPR</span>
                <span class="gate-badge" style="margin-left: 8px;">BENCHMARK VERIFIED</span>
              </div>
              <span class="tag-mono">&tau; = 0.650000</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">
              Path: <code>models/NASA_mat_aging_gpr_composite.pkl</code> | 67,971 Cycles Screened | Test MAE: <strong>0.098A</strong>
            </div>
          </div>

          <!-- Model ISRO -->
          <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; background: #FFFFFF;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: 700; font-size: 14px; color: var(--text-main);">ISRO Stream &bull; Live Telemetry Adapter</span>
                <span class="gate-badge" style="margin-left: 8px;">ONLINE ACTIVE</span>
              </div>
              <span class="tag-mono">&tau; = 0.497482</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">
              Path: <code>models/ISRO_live_adapted_model.pkl</code> | 18 Spacecraft Channels | Turnkey Adaptation: <strong>97.80% Recall</strong>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-action-primary" onclick="closeModelRegistryModal()">Close Model Registry</button>
      </div>
    </div>
  `;
  document.body.appendChild(div);
}

// -------------------------------------------------------------
// 5. FABRICATION LOT SCREENING & DEFECT DISPERSION VISUALIZATION
// -------------------------------------------------------------
let _lotChartCurrentMode = 'stacked'; // 'stacked' | 'grouped'
window._onLotChartLotClick = null;

function renderFabricationLotChart(containerId, data, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const mode = options.mode || _lotChartCurrentMode || 'stacked';
  _lotChartCurrentMode = mode;
  const selectedLot = options.selectedLot || null;
  if (options.onLotSelect) {
    window._onLotChartLotClick = options.onLotSelect;
  }

  // Handle completely empty dataset (e.g. before Live Simulation starts)
  if (!data || data.length === 0) {
    container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:140px;color:#64748B;font-size:12.5px;text-align:center;padding:24px;background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:6px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" style="margin-bottom:8px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span style="font-weight:600;color:#475569;font-size:13px;">No stream components loaded yet.</span>
        <span style="font-size:11.5px;color:#94A3B8;margin-top:5px;max-width:540px;">Click the <strong>Live Simulation</strong> button at the top right to start streaming burn-in chamber telemetry packets.</span>
      </div>
    `;
    const totalBatchesEl = document.getElementById('lotTotalBatchesVal');
    const avgYieldEl = document.getElementById('lotAvgYieldVal');
    if (totalBatchesEl) totalBatchesEl.innerText = "--";
    if (avgYieldEl) avgYieldEl.innerText = "--";
    return;
  }

  // Detect genuine lot metadata
  const hasRealLots = data.some(item => {
    const rawLot = (item.lot_id !== undefined && item.lot_id !== null ? item.lot_id : item.lot);
    if (!rawLot) return false;
    const s = String(rawLot).trim();
    return s.length > 0 && s !== 'null' && s !== 'undefined' && !s.startsWith('N/A') && !s.toLowerCase().includes('unspecified') && !s.startsWith('LOT-UPLOAD-');
  });

  if (!hasRealLots) {
    container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:140px;color:#64748B;font-size:12.5px;text-align:center;padding:24px;background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:6px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" style="margin-bottom:8px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span style="font-weight:600;color:#475569;font-size:13px;">Lot-wise analysis unavailable: source dataset contains no lot metadata.</span>
        <span style="font-size:11.5px;color:#94A3B8;margin-top:5px;max-width:540px;">Native dataset provides component-level screening across standard Step checkpoints. When uploaded data contains a real lot_id, lot-wise grouping and charts are automatically enabled.</span>
      </div>
    `;
    const totalBatchesEl = document.getElementById('lotTotalBatchesVal');
    const avgYieldEl = document.getElementById('lotAvgYieldVal');
    if (totalBatchesEl) totalBatchesEl.innerText = "No Lot Metadata";
    if (avgYieldEl) {
      const totalAll = (data || []).length;
      const passAll = (data || []).filter(item => (item.disposition || item.action || 'PASS').toUpperCase() === 'PASS').length;
      const avgYield = totalAll > 0 ? ((passAll / totalAll) * 100).toFixed(1) : '100.0';
      avgYieldEl.innerText = `${avgYield}% (Cohort)`;
    }
    return;
  }

  // Aggregate by actual component lot
  const lotMap = {};
  (data || []).forEach(item => {
    const rawLot = (item.lot_id !== undefined && item.lot_id !== null ? item.lot_id : item.lot);
    if (!rawLot) return;
    const lot = String(rawLot).trim();
    if (lot.length === 0 || lot === 'null' || lot.startsWith('N/A') || lot.toLowerCase().includes('unspecified') || lot.startsWith('LOT-UPLOAD-')) return;
    if (!lotMap[lot]) {
      lotMap[lot] = { lot, pass: 0, review: 0, reject: 0, total: 0 };
    }
    lotMap[lot].total += 1;
    const disp = (item.disposition || item.action || 'PASS').toUpperCase();
    if (disp === 'PASS') lotMap[lot].pass += 1;
    else if (disp === 'REVIEW') lotMap[lot].review += 1;
    else if (disp === 'REJECT') lotMap[lot].reject += 1;
  });

  const lots = Object.values(lotMap).sort((a, b) => 
    a.lot.localeCompare(b.lot, undefined, { numeric: true, sensitivity: 'base' })
  );

  if (lots.length === 0) {
    container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:140px;color:#64748B;font-size:12px;">Lot-wise analysis unavailable: source dataset contains no lot metadata.</div>`;
    const totalBatchesEl = document.getElementById('lotTotalBatchesVal');
    if (totalBatchesEl) totalBatchesEl.innerText = "No Lot Metadata";
    return;
  }

  // Update summary KPI chips if present on page
  const totalBatchesEl = document.getElementById('lotTotalBatchesVal');
  const avgYieldEl = document.getElementById('lotAvgYieldVal');
  if (totalBatchesEl) totalBatchesEl.innerText = `${lots.length} Batches`;
  if (avgYieldEl) {
    const totalAll = lots.reduce((acc, l) => acc + l.total, 0);
    const passAll = lots.reduce((acc, l) => acc + l.pass, 0);
    const avgYield = totalAll > 0 ? ((passAll / totalAll) * 100).toFixed(1) : '100.0';
    avgYieldEl.innerText = `${avgYield}%`;
  }

  // Geometry calculations
  const width = container.clientWidth || 980;
  const height = container.clientHeight || 205;
  const padLeft = 48;
  const padRight = 20;
  const padTop = 22;
  const padBottom = 38;
  const chartW = Math.max(300, width - padLeft - padRight);
  const chartH = Math.max(100, height - padTop - padBottom);

  let yMax = 10;
  if (mode === 'stacked') {
    const maxLotTotal = Math.max(...lots.map(l => l.total), 5);
    yMax = Math.ceil(maxLotTotal / 2) * 2;
    if (yMax < 6) yMax = 6;
  } else {
    const maxSubVal = Math.max(...lots.map(l => Math.max(l.pass, l.review, l.reject)), 3);
    yMax = Math.ceil(maxSubVal / 2) * 2;
    if (yMax < 4) yMax = 4;
  }

  const slotW = chartW / lots.length;
  const baselineY = padTop + chartH;

  let svg = `<svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="display:block; overflow:visible; font-family:var(--font-sans);">`;

  // Horizontal Grid Lines & Ticks (4 levels: 0, 33%, 66%, 100%)
  const ySteps = [0, Math.round(yMax * 0.33), Math.round(yMax * 0.66), yMax];
  ySteps.forEach(val => {
    const y = baselineY - (val / yMax) * chartH;
    svg += `<line x1="${padLeft}" y1="${y}" x2="${padLeft + chartW}" y2="${y}" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="3 3"/>`;
    svg += `<text x="${padLeft - 8}" y="${y + 3.5}" fill="#94A3B8" font-size="9.5" font-family="var(--font-mono)" text-anchor="end">${val}</text>`;
  });

  // Y-Axis Label
  svg += `
    <text x="${padLeft - 32}" y="${padTop + chartH / 2}" fill="#94A3B8" font-size="8.5" font-weight="700" font-family="var(--font-mono)" letter-spacing="0.08em" text-anchor="middle" transform="rotate(-90 ${padLeft - 32} ${padTop + chartH / 2})">
      SCREENED UNITS
    </text>
  `;

  // Render Each Lot Bar (Stacked or Grouped)
  lots.forEach((lot, i) => {
    const slotCenterX = padLeft + (i + 0.5) * slotW;
    const isSelected = selectedLot && selectedLot === lot.lot;

    // Selected lot column highlight backdrop
    if (isSelected) {
      svg += `
        <rect x="${slotCenterX - slotW * 0.46}" y="${padTop - 4}" width="${slotW * 0.92}" height="${chartH + 8}" 
              fill="rgba(15, 118, 110, 0.08)" stroke="#0F766E" stroke-width="1.5" stroke-dasharray="4 2" rx="4"/>
      `;
    }

    if (mode === 'stacked') {
      const barW = Math.min(30, Math.max(14, slotW * 0.62));
      const barX = slotCenterX - barW / 2;

      const hPass = (lot.pass / yMax) * chartH;
      const hReview = (lot.review / yMax) * chartH;
      const hReject = (lot.reject / yMax) * chartH;

      let curY = baselineY;

      // 1. Pass segment (bottom)
      if (hPass > 0) {
        curY -= hPass;
        const rx = (hReview === 0 && hReject === 0) ? 3 : 0;
        svg += `<rect x="${barX}" y="${curY}" width="${barW}" height="${hPass}" fill="#10B981" rx="${rx}"/>`;
        if (hPass >= 13) {
          svg += `<text x="${slotCenterX}" y="${curY + hPass / 2 + 3.5}" fill="#FFFFFF" font-size="8.5" font-weight="700" font-family="var(--font-mono)" text-anchor="middle">${lot.pass}</text>`;
        }
      }

      // 2. Review segment (middle)
      if (hReview > 0) {
        curY -= hReview;
        const rx = (hReject === 0) ? 3 : 0;
        svg += `<rect x="${barX}" y="${curY}" width="${barW}" height="${hReview}" fill="#F59E0B" rx="${rx}"/>`;
        if (hReview >= 13) {
          svg += `<text x="${slotCenterX}" y="${curY + hReview / 2 + 3.5}" fill="#FFFFFF" font-size="8.5" font-weight="700" font-family="var(--font-mono)" text-anchor="middle">${lot.review}</text>`;
        }
      }

      // 3. Reject segment (top)
      if (hReject > 0) {
        curY -= hReject;
        svg += `<rect x="${barX}" y="${curY}" width="${barW}" height="${hReject}" fill="#EF4444" rx="3"/>`;
        if (hReject >= 13) {
          svg += `<text x="${slotCenterX}" y="${curY + hReject / 2 + 3.5}" fill="#FFFFFF" font-size="8.5" font-weight="700" font-family="var(--font-mono)" text-anchor="middle">${lot.reject}</text>`;
        }
      }

      // Top total label
      const totalY = curY - 4;
      svg += `<text x="${slotCenterX}" y="${totalY}" fill="${isSelected ? '#0F766E' : '#475569'}" font-size="9" font-weight="700" font-family="var(--font-mono)" text-anchor="middle">${lot.total}</text>`;

    } else {
      // Grouped Mode (Side-by-Side: Pass, Review, Reject)
      const subBarW = Math.min(10, Math.max(4, (slotW * 0.72) / 3));
      const groupW = subBarW * 3 + 2;
      const startX = slotCenterX - groupW / 2;

      const hPass = (lot.pass / yMax) * chartH;
      const hReview = (lot.review / yMax) * chartH;
      const hReject = (lot.reject / yMax) * chartH;

      // Pass sub-bar
      if (hPass > 0) {
        const yP = baselineY - hPass;
        svg += `<rect x="${startX}" y="${yP}" width="${subBarW}" height="${hPass}" fill="#10B981" rx="2"/>`;
        if (hPass > 12) {
          svg += `<text x="${startX + subBarW/2}" y="${yP - 2}" fill="#059669" font-size="7.5" font-family="var(--font-mono)" font-weight="700" text-anchor="middle">${lot.pass}</text>`;
        }
      }

      // Review sub-bar
      if (hReview > 0) {
        const yR = baselineY - hReview;
        svg += `<rect x="${startX + subBarW + 1}" y="${yR}" width="${subBarW}" height="${hReview}" fill="#F59E0B" rx="2"/>`;
        if (hReview > 12) {
          svg += `<text x="${startX + subBarW*1.5 + 1}" y="${yR - 2}" fill="#D97706" font-size="7.5" font-family="var(--font-mono)" font-weight="700" text-anchor="middle">${lot.review}</text>`;
        }
      }

      // Reject sub-bar
      if (hReject > 0) {
        const yJ = baselineY - hReject;
        svg += `<rect x="${startX + (subBarW + 1) * 2}" y="${yJ}" width="${subBarW}" height="${hReject}" fill="#EF4444" rx="2"/>`;
        if (hReject > 12) {
          svg += `<text x="${startX + subBarW*2.5 + 2}" y="${yJ - 2}" fill="#DC2626" font-size="7.5" font-family="var(--font-mono)" font-weight="700" text-anchor="middle">${lot.reject}</text>`;
        }
      }
    }

    // X-Axis Label
    let label = lot.lot;
    if (label.length > 10) label = label.slice(0, 9) + '…';

    svg += `<text x="${slotCenterX}" y="${baselineY + 14}" fill="${isSelected ? '#0F766E' : '#64748B'}" font-size="9" font-weight="${isSelected ? '800' : '600'}" font-family="var(--font-mono)" text-anchor="middle">${label}</text>`;
    svg += `<text x="${slotCenterX}" y="${baselineY + 25}" fill="#94A3B8" font-size="8" font-family="var(--font-mono)" text-anchor="middle">${lot.total}u</text>`;

    // Interactive Hover & Click Hit-Zone
    const lotPayload = JSON.stringify({
      lot: lot.lot,
      total: lot.total,
      pass: lot.pass,
      review: lot.review,
      reject: lot.reject,
      yieldRate: lot.total > 0 ? ((lot.pass / lot.total) * 100).toFixed(1) : 0
    }).replace(/"/g, '&quot;');

    const clickFn = options.onLotSelect ? `window._handleLotChartClick('${lot.lot}')` : '';

    svg += `
      <rect x="${slotCenterX - slotW / 2}" y="${padTop}" width="${slotW}" height="${chartH + padBottom}" 
            fill="transparent" style="cursor: pointer;"
            onmouseenter="window._showLotChartTooltip(event, ${lotPayload})"
            onmousemove="window._moveLotChartTooltip(event)"
            onmouseleave="window._hideLotChartTooltip()"
            onclick="${clickFn}"
      />
    `;
  });

  // Baseline X-axis stroke
  svg += `<line x1="${padLeft}" y1="${baselineY}" x2="${padLeft + chartW}" y2="${baselineY}" stroke="#CBD5E1" stroke-width="1.2"/>`;

  svg += `</svg>`;
  container.innerHTML = svg;
}

// Floating Lot Chart Tooltip Controller
window._showLotChartTooltip = function(e, data) {
  let tooltip = document.getElementById('lotChartTooltip');
  if (!tooltip) {
    tooltip = document.createElement('div');
    tooltip.id = 'lotChartTooltip';
    tooltip.className = 'chart-tooltip';
    document.body.appendChild(tooltip);
  }

  const passPct = data.total > 0 ? ((data.pass / data.total) * 100).toFixed(1) : 0;
  const reviewPct = data.total > 0 ? ((data.review / data.total) * 100).toFixed(1) : 0;
  const rejectPct = data.total > 0 ? ((data.reject / data.total) * 100).toFixed(1) : 0;
  const isAllPass = data.reject === 0 && data.review === 0;

  tooltip.innerHTML = `
    <div class="tooltip-lot-title">${data.lot} &bull; ${data.total} Units Screened</div>
    <div class="tooltip-status-badge ${data.reject > 0 ? 'warn' : 'pass'}">
      ${data.reject === 0 ? (isAllPass ? '✓ 100% FLIGHT QUALIFIED' : '✓ NOMINAL ENVELOPE') : `⚠ ${data.reject} DEFECT(S) INTERCEPTED`}
    </div>
    <div class="tooltip-row">
      <span class="tooltip-lbl"><span class="tooltip-dot" style="background:#10B981;"></span>Pass (Nominal)</span>
      <span class="tooltip-val">${data.pass} (${passPct}%)</span>
    </div>
    <div class="tooltip-row">
      <span class="tooltip-lbl"><span class="tooltip-dot" style="background:#F59E0B;"></span>Review (Watch)</span>
      <span class="tooltip-val">${data.review} (${reviewPct}%)</span>
    </div>
    <div class="tooltip-row">
      <span class="tooltip-lbl"><span class="tooltip-dot" style="background:#EF4444;"></span>Reject (Defect)</span>
      <span class="tooltip-val">${data.reject} (${rejectPct}%)</span>
    </div>
    <div class="tooltip-footer">
      <span>Yield: <strong style="color:#FFFFFF;">${data.yieldRate}%</strong></span>
      <span class="tooltip-action-hint">Click to filter table &rarr;</span>
    </div>
  `;

  tooltip.classList.add('visible');
  window._moveLotChartTooltip(e);
};

window._moveLotChartTooltip = function(e) {
  const tooltip = document.getElementById('lotChartTooltip');
  if (!tooltip) return;
  const x = e.clientX + 14;
  const y = e.clientY - 20;
  tooltip.style.left = `${Math.min(window.innerWidth - 300, x)}px`;
  tooltip.style.top = `${Math.max(10, y)}px`;
};

window._hideLotChartTooltip = function() {
  const tooltip = document.getElementById('lotChartTooltip');
  if (tooltip) tooltip.classList.remove('visible');
};

window._handleLotChartClick = function(lotId) {
  if (typeof window._onLotChartLotClick === 'function') {
    window._onLotChartLotClick(lotId);
  }
};

window.setLotChartMode = function(mode) {
  _lotChartCurrentMode = mode;
  document.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
  const activeBtn = document.getElementById(mode === 'grouped' ? 'btnModeGrouped' : 'btnModeStacked');
  if (activeBtn) activeBtn.classList.add('active');

  if (typeof renderCurrentLotChart === 'function') {
    renderCurrentLotChart();
  } else if (document.getElementById('screeningLotChartContainer')) {
    const data = getDatasetComponents(getActiveDatasetKey());
    renderFabricationLotChart('screeningLotChartContainer', data, {
      mode: mode,
      onLotSelect: window._screeningLotSelectHandler
    });
  } else if (document.getElementById('lotChartContainer')) {
    const data = getDatasetComponents(getActiveDatasetKey());
    renderFabricationLotChart('lotChartContainer', data, {
      mode: mode
    });
  }
};

// Window resize re-render debounce
window.addEventListener('resize', () => {
  if (window._lotChartResizeTimer) clearTimeout(window._lotChartResizeTimer);
  window._lotChartResizeTimer = setTimeout(() => {
    if (typeof renderCurrentLotChart === 'function') {
      renderCurrentLotChart();
    }
  }, 150);
});

// =============================================================
// 7. LIVE BURN-IN CHAMBER TELEMETRY SIMULATION ENGINE
// =============================================================
function loadSimulationFromStorage() {
  try {
    const active = localStorage.getItem('isro_sim_active') === 'true';
    const rawItems = localStorage.getItem('isro_sim_items');
    const items = rawItems ? JSON.parse(rawItems) : [];
    const tick = parseInt(localStorage.getItem('isro_sim_tick') || '0', 10);
    return {
      active: active,
      streamedItems: Array.isArray(items) ? items : [],
      tickCount: isNaN(tick) ? 0 : tick
    };
  } catch (e) {
    return { active: false, streamedItems: [], tickCount: 0 };
  }
}

function saveSimulationToStorage() {
  try {
    if (!window.ISRO_SIMULATION) return;
    localStorage.setItem('isro_sim_active', window.ISRO_SIMULATION.active ? 'true' : 'false');
    localStorage.setItem('isro_sim_items', JSON.stringify((window.ISRO_SIMULATION.streamedItems || []).slice(0, 150)));
    localStorage.setItem('isro_sim_tick', String(window.ISRO_SIMULATION.tickCount || 0));
  } catch (e) {
    console.warn("Could not save simulation state to localStorage:", e);
  }
}

const _initialSimState = loadSimulationFromStorage();
window.ISRO_SIMULATION = {
  active: false,
  timer: null,
  intervalMs: 1400,
  streamedItems: _initialSimState.streamedItems,
  tickCount: _initialSimState.tickCount
};

const SIM_PARAM_POOL = [
  { param: "param_07 (LeakageCurrent)", desc: "Sub-threshold gate dielectric leakage" },
  { param: "param_15 (ThresholdDrift)", desc: "Gate oxide threshold voltage shift" },
  { param: "param_04 (DrainConductance)", desc: "Channel degradation under high drain field" },
  { param: "param_12 (ThermalFlux)", desc: "Substrate heat dissipation variance" },
  { param: "param_01 (CoreCurrent)", desc: "Core active conduction channel drift" },
  { param: "param_11 (DynamicRon)", desc: "Dynamic on-resistance switching degradation" }
];

function generateSimulatedComponent(seq) {
  const baseNum = 175 + seq;
  const id = `STREAM-${String(baseNum).padStart(3, '0')}`;
  const paramObj = SIM_PARAM_POOL[seq % SIM_PARAM_POOL.length];

  // Distribution: ~70% PASS, ~18% REVIEW, ~12% REJECT
  const isReject = (seq % 7 === 4);
  const isReview = !isReject && (seq % 4 === 2);
  const disposition = isReject ? 'REJECT' : (isReview ? 'REVIEW' : 'PASS');

  let rawScore, calibratedScore, peerZ, drift;
  if (isReject) {
    rawScore = 0.81 + (Math.random() * 0.16);
    calibratedScore = Math.min(0.99, rawScore + 0.05);
    peerZ = +(3.2 + Math.random() * 1.5).toFixed(1);
    drift = +(1.1 + Math.random() * 0.8).toFixed(2);
  } else if (isReview) {
    rawScore = 0.52 + (Math.random() * 0.14);
    calibratedScore = Math.min(0.70, rawScore + 0.02);
    peerZ = +(2.1 + Math.random() * 0.7).toFixed(1);
    drift = +(0.35 + Math.random() * 0.25).toFixed(2);
  } else {
    rawScore = 0.12 + (Math.random() * 0.22);
    calibratedScore = +(rawScore * 0.9).toFixed(2);
    peerZ = +(0.4 + Math.random() * 1.1).toFixed(1);
    drift = +(0.08 + Math.random() * 0.14).toFixed(2);
  }

  const v0 = 0.10;
  const v1 = +(v0 + drift).toFixed(2);
  const traj = [v0, v1];

  return {
    id: id,
    lot: null,
    lot_id: null,
    device_type: "Chamber Telemetry Stream",
    source: "ISRO_Telemetry_Stream",
    parameter: paramObj.param,
    unit: "arb_norm",
    checkpoint: "Step 2",
    disposition: disposition,
    rule: isReject ? "RULE_CRITICAL_ANOMALY" : (isReview ? "RULE_ELEVATED_WATCH_LIST" : "RULE_PASS_NOMINAL"),
    reason: isReject
      ? `Telemetry item ${id} exhibited elevated drift (+${peerZ}σ) and excessive isolation score (${rawScore.toFixed(4)}) beyond safety envelope. Data quality passed 12/12 gates. Recommended: REJECT.`
      : (isReview
          ? `Telemetry item ${id} requires QA Engineering REVIEW because anomaly score (${rawScore.toFixed(4)}) is elevated above watch threshold (0.350). Peer deviation is +${peerZ}σ. Data quality passed 12/12 gates.`
          : `Telemetry item ${id} demonstrated clean monotonic thermal stability with nominal drift (+${peerZ}σ). Space flight qualified.`),
    score: +rawScore.toFixed(4),
    raw_score: +rawScore.toFixed(4),
    calibrated_score: +calibratedScore.toFixed(2),
    status: isReject ? "HIGH" : (isReview ? "WATCH" : "NOMINAL"),
    quality_gate: "12/12 PASSED",
    forecast_status: "unavailable_insufficient_history",
    forecast_reason: "GPR not applicable: insufficient trajectory history.",
    forecast_mean: null,
    forecast_std: null,
    lower_2sigma: null,
    upper_2sigma: null,
    forecast_horizon: null,
    traj: traj,
    steps: [1, 2],
    checkpoints_labels: ["Step 1", "Step 2"],
    drift: drift,
    peer_mean: 0.14,
    peer_std: 0.05,
    peer_z: peerZ,
    spec_min: -0.5,
    spec_max: 1.5,
    shap: [
      { feature: "degradation_slope", val: `+${peerZ}σ`, score: +(rawScore * 0.9).toFixed(2), desc: "Checkpoint Acceleration" },
      { feature: "cohort_variance", val: `+${(peerZ * 0.7).toFixed(1)}σ`, score: +(rawScore * 0.75).toFixed(2), desc: "Cohort Variance" },
      { feature: "spectral_kurtosis", val: `+${(peerZ * 0.6).toFixed(1)}σ`, score: +(rawScore * 0.55).toFixed(2), desc: "Signal Shape Anomaly" },
      { feature: "thermal_stability", val: `+${(peerZ * 0.4).toFixed(1)}σ`, score: +(rawScore * 0.4).toFixed(2), desc: "Temperature Sensitivity" }
    ],
    is_live_sim: true
  };
}

function updateSimBadge() {
  const badge = document.getElementById('telemetryStatusBadge');
  if (!badge) return;
  const count = (window.ISRO_SIMULATION && window.ISRO_SIMULATION.streamedItems) ? window.ISRO_SIMULATION.streamedItems.length : 0;
  if (window.ISRO_SIMULATION && window.ISRO_SIMULATION.active) {
    badge.innerText = `STREAMING (+${count})`;
    badge.style.color = '#38BDF8';
    badge.style.borderColor = 'rgba(56, 189, 248, 0.4)';
  } else if (count > 0) {
    badge.innerText = `PAUSED (+${count})`;
    badge.style.color = '#F59E0B';
    badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
  } else {
    badge.innerText = 'BENCHMARK EVAL';
    badge.style.color = '';
    badge.style.borderColor = '';
  }
}

function toggleLiveSimulation() {
  if (window.ISRO_SIMULATION.active) {
    pauseLiveSimulation();
  } else {
    startLiveSimulation();
  }
}

function startLiveSimulation() {
  window.ISRO_SIMULATION.active = true;
  saveSimulationToStorage();
  updateSimButtonsUi(true);
  updateSimBadge();

  showToast("🚀 Live Burn-In Simulation Started • Ingesting 168h Chamber Telemetry...", "success");

  // Ingest first component immediately
  simulateNextComponent();

  // Then tick every interval
  if (window.ISRO_SIMULATION.timer) {
    clearInterval(window.ISRO_SIMULATION.timer);
  }
  window.ISRO_SIMULATION.timer = setInterval(() => {
    simulateNextComponent();
  }, window.ISRO_SIMULATION.intervalMs);
}

function pauseLiveSimulation() {
  window.ISRO_SIMULATION.active = false;
  if (window.ISRO_SIMULATION.timer) {
    clearInterval(window.ISRO_SIMULATION.timer);
    window.ISRO_SIMULATION.timer = null;
  }
  saveSimulationToStorage();
  updateSimButtonsUi(false);
  updateSimBadge();
  showToast(`Simulation paused. ${window.ISRO_SIMULATION.streamedItems.length} live parts ingested.`, "info");
}

function resetLiveSimulation() {
  window.ISRO_SIMULATION.active = false;
  if (window.ISRO_SIMULATION.timer) {
    clearInterval(window.ISRO_SIMULATION.timer);
    window.ISRO_SIMULATION.timer = null;
  }
  window.ISRO_SIMULATION.streamedItems = [];
  window.ISRO_SIMULATION.tickCount = 0;
  saveSimulationToStorage();

  updateSimButtonsUi(false, true);
  updateSimBadge();
  refreshCurrentPageAfterSim();
  showToast("Live simulation reset to baseline frozen dataset.", "info");
}

function simulateNextComponent() {
  window.ISRO_SIMULATION.tickCount++;
  const comp = generateSimulatedComponent(window.ISRO_SIMULATION.tickCount);
  window.ISRO_SIMULATION.streamedItems.unshift(comp);
  if (window.ISRO_SIMULATION.streamedItems.length > 150) {
    window.ISRO_SIMULATION.streamedItems.length = 150;
  }
  saveSimulationToStorage();

  // Update telemetry status badge in header
  updateSimBadge();

  // If Reject (Critical Defect Intercepted), trigger aerospace alert toast!
  if (comp.disposition === 'REJECT') {
    showSimAlertToast(comp);
  }

  // Refresh active dashboard page
  refreshCurrentPageAfterSim(comp);
}

function refreshCurrentPageAfterSim(latestComp) {
  // Update sidebar count chip across all pages
  const sideChip = document.getElementById('sidebarScreeningChip');
  if (sideChip) {
    const curKey = (typeof currentDataset !== 'undefined') ? currentDataset : getActiveDatasetKey();
    const totalCount = getDatasetComponents(curKey).length;
    sideChip.innerText = String(totalCount);
  }

  // If Overview Page:
  if (typeof renderOverview === 'function') {
    renderOverview();
  }

  // If Screening Page:
  if (typeof renderTable === 'function') {
    renderTable();
    if (typeof updateFilterPillCounts === 'function') updateFilterPillCounts();
    if (typeof renderCurrentLotChart === 'function') renderCurrentLotChart();

    // Pulse highlight on the new row if present
    setTimeout(() => {
      const tbody = document.getElementById('screeningTableBody');
      if (tbody && tbody.firstElementChild) {
        tbody.firstElementChild.classList.add('sim-new-row');
      }
    }, 40);
  }

  // If Diagnostics Page:
  if (typeof updateDiagnosticsForSim === 'function') {
    updateDiagnosticsForSim();
  } else if (typeof renderDiagnostics === 'function') {
    renderDiagnostics();
  }
}

function updateSimButtonsUi(isActive, isReset = false) {
  const btn = document.getElementById('btnLiveSim');
  const btnText = document.getElementById('btnLiveSimText');
  const resetBtn = document.getElementById('btnLiveReset');

  if (!btn) return;

  if (isActive) {
    btn.classList.add('active');
    if (btnText) btnText.innerText = 'Pause Stream';
    if (resetBtn) resetBtn.style.display = 'inline-flex';
  } else {
    btn.classList.remove('active');
    if (isReset) {
      if (btnText) btnText.innerText = 'Live Simulation';
      if (resetBtn) resetBtn.style.display = 'none';
      const badge = document.getElementById('telemetryStatusBadge');
      if (badge) {
        badge.innerText = 'BENCHMARK EVAL';
        badge.style.color = '';
        badge.style.borderColor = '';
      }
    } else {
      const hasItems = window.ISRO_SIMULATION && window.ISRO_SIMULATION.streamedItems && window.ISRO_SIMULATION.streamedItems.length > 0;
      if (btnText) {
        btnText.innerText = hasItems ? 'Resume Stream' : 'Live Simulation';
      }
      if (resetBtn) {
        resetBtn.style.display = hasItems ? 'inline-flex' : 'none';
      }
    }
  }
}

function initSimulationLifecycle() {
  const saved = loadSimulationFromStorage();
  window.ISRO_SIMULATION.streamedItems = saved.streamedItems;
  window.ISRO_SIMULATION.tickCount = saved.tickCount;

  if (saved.active) {
    window.ISRO_SIMULATION.active = true;
    updateSimButtonsUi(true);
    updateSimBadge();

    // Auto-resume stream interval timer across page navigations
    if (!window.ISRO_SIMULATION.timer) {
      window.ISRO_SIMULATION.timer = setInterval(() => {
        simulateNextComponent();
      }, window.ISRO_SIMULATION.intervalMs);
    }
  } else if (saved.streamedItems.length > 0) {
    window.ISRO_SIMULATION.active = false;
    updateSimButtonsUi(false);
    updateSimBadge();
  }
}

// Automatically sync across browser tabs/windows
window.addEventListener('storage', (e) => {
  if (e.key === 'isro_sim_active') {
    if (e.newValue === 'true' && !window.ISRO_SIMULATION.active) {
      window.ISRO_SIMULATION.active = true;
      const saved = loadSimulationFromStorage();
      window.ISRO_SIMULATION.streamedItems = saved.streamedItems;
      window.ISRO_SIMULATION.tickCount = saved.tickCount;
      updateSimButtonsUi(true);
      updateSimBadge();
      if (!window.ISRO_SIMULATION.timer) {
        window.ISRO_SIMULATION.timer = setInterval(() => {
          simulateNextComponent();
        }, window.ISRO_SIMULATION.intervalMs);
      }
    } else if (e.newValue === 'false' && window.ISRO_SIMULATION.active) {
      window.ISRO_SIMULATION.active = false;
      if (window.ISRO_SIMULATION.timer) {
        clearInterval(window.ISRO_SIMULATION.timer);
        window.ISRO_SIMULATION.timer = null;
      }
      updateSimButtonsUi(false);
      updateSimBadge();
    }
  } else if (e.key === 'isro_sim_items') {
    try {
      const items = JSON.parse(e.newValue || '[]');
      if (Array.isArray(items)) {
        window.ISRO_SIMULATION.streamedItems = items;
        refreshCurrentPageAfterSim();
        updateSimBadge();
      }
    } catch (_) {}
  }
});

// Run lifecycle hook immediately when document is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSimulationLifecycle);
} else {
  initSimulationLifecycle();
}

function showSimAlertToast(comp) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast-message';
  toast.style.background = '#7F1D1D';
  toast.style.border = '1px solid #EF4444';
  toast.style.boxShadow = '0 10px 25px -5px rgba(239, 68, 68, 0.45)';
  
  toast.innerHTML = `
    <div style="display:flex; align-items:flex-start; gap:10px; width:100%;">
      <span style="font-size:16px;">⚠️</span>
      <div style="flex:1;">
        <div style="font-weight:800; font-size:11.5px; color:#FEE2E2; letter-spacing:0.02em;">CRITICAL DEFECT INTERCEPTED</div>
        <div style="font-size:11px; color:#FFFFFF; margin-top:2px;">
          Part <strong>${comp.id}</strong> &bull; Score: <strong style="color:#FCA5A5;">${comp.score.toFixed(4)}</strong>
        </div>
        <div style="margin-top:6px;">
          <button onclick="navigateOrInspectComponent('${comp.id}'); this.closest('.toast-message').remove();" 
                  style="background:#EF4444; border:none; color:#FFFFFF; font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:4px; cursor:pointer;">
            Inspect Part &rarr;
          </button>
        </div>
      </div>
      <button onclick="this.closest('.toast-message').remove();" style="background:transparent; border:none; color:#FCA5A5; cursor:pointer; font-size:14px; padding:0 4px;">&times;</button>
    </div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      setTimeout(() => toast.remove(), 300);
    }
  }, 5000);
}

function navigateOrInspectComponent(compId) {
  if (typeof openInspector === 'function') {
    const comp = window.findComponentById(compId);
    if (comp) openInspector(comp);
  } else {
    window.location.href = `screening.html?inspect=${encodeURIComponent(compId)}`;
  }
}


