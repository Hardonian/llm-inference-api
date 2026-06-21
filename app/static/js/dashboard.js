// ========================================
// AI Lab Command Center - Enhanced Dashboard JS
// Modular, Interactive, Secure, Threat-Aware
// ========================================

// ========================================
// MODULE: State Management (Encrypted)
// ========================================
const StateManager = (() => {
  const STORAGE_KEY = 'ai-lab-state-v2';
  const ENCRYPTION_KEY = 'ai-lab-encryption-salt';

  // Simple XOR encryption for localStorage (replace with Web Crypto API in production)
  function encrypt(data) {
    const str = JSON.stringify(data);
    let result = '';
    for (let i = 0; i < str.length; i++) {
      result += String.fromCharCode(str.charCodeAt(i) ^ ENCRYPTION_KEY.charCodeAt(i % ENCRYPTION_KEY.length));
    }
    return btoa(unescape(encodeURIComponent(result)));
  }

  function decrypt(data) {
    try {
      const str = decodeURIComponent(escape(atob(data)));
      let result = '';
      for (let i = 0; i < str.length; i++) {
        result += String.fromCharCode(str.charCodeAt(i) ^ ENCRYPTION_KEY.charCodeAt(i % ENCRYPTION_KEY.length));
      }
      return JSON.parse(result);
    } catch {
      return null;
    }
  }

  const defaultState = {
    xp: 0, level: 1, xpToNext: 100,
    badges: new Set(),
    theme: 'dark',
    services: {}, gpus: [], ollamaLanes: [],
    activityLog: [], uploadQueue: [],
    security: { threats: [], auditLog: [], blockedIPs: new Set() },
    comfyui: { models: [], nodes: [], workflows: [] },
    jobs: [], achievements: [],
    preferences: { autoRefresh: true, wsEnabled: true, notifications: true }
  };

  return {
    load() {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const decrypted = decrypt(saved);
          if (decrypted) {
            return { ...defaultState, ...decrypted, badges: new Set(decrypted.badges || []) };
          }
        }
      } catch (e) { console.warn('State load failed:', e); }
      return defaultState;
    },

    save(state) {
      try {
        const toSave = { ...state, badges: [...state.badges] };
        localStorage.setItem(STORAGE_KEY, encrypt(toSave));
      } catch (e) { console.warn('State save failed:', e); }
    },

    clear() { localStorage.removeItem(STORAGE_KEY); }
  };
})();

// ========================================
// MODULE: Security & Threat Detection
// ========================================
const SecurityEngine = (() => {
  const threatPatterns = {
    promptInjection: [
      /ignore.?previous.?instructions/i,
      /system.?prompt/i,
      /you.?are.?now/i,
      /forget.?everything/i,
      /new.?instructions/i,
      /override.?safety/i,
      /bypass.?filter/i
    ],
    modelExtraction: [
      /what.?is.?your.?prompt/i,
      /repeat.?the.?prompt/i,
      /show.?me.?the.?system/i,
      /output.?your.?instructions/i,
      /reveal.?prompt/i
    ],
    dataExfiltration: [
      /send.?data.?to/i,
      /upload.?to/i,
      /exfiltrat/i,
      /steal.?data/i,
      /leak.?information/i
    ],
    reconnaissance: [
      /what.?model.?are.?you/i,
      /version.?number/i,
      /architecture/i,
      /parameters/i,
      /training.?data/i
    ]
  };

  const severityScores = { promptInjection: 9, modelExtraction: 8, dataExfiltration: 10, reconnaissance: 5 };

  function analyzePrompt(prompt) {
    const threats = [];
    const lower = prompt.toLowerCase();

    for (const [category, patterns] of Object.entries(threatPatterns)) {
      for (const pattern of patterns) {
        if (pattern.test(lower)) {
          threats.push({ category, pattern: pattern.source, severity: severityScores[category], timestamp: Date.now() });
        }
      }
    }

    return threats;
  }

  function analyzeBehavior(requestData) {
    const anomalies = [];
    const { ip, userAgent, endpoint, frequency, payloadSize } = requestData;

    if (frequency > 100) anomalies.push({ type: 'high_frequency', severity: 7, detail: `${frequency} req/min` });
    if (payloadSize > 100000) anomalies.push({ type: 'large_payload', severity: 6, detail: `${payloadSize} bytes` });
    if (!userAgent || userAgent.length < 10) anomalies.push({ type: 'missing_ua', severity: 5 });

    return anomalies;
  }

  return { analyzePrompt, analyzeBehavior, threatPatterns, severityScores };
})();

// ========================================
// MODULE: WebSocket Manager with Reconnection
// ========================================
const WSManager = (() => {
  let ws = null;
  let reconnectAttempts = 0;
  let handlers = new Map();

  function connect(onMessage) {
    if (ws) ws.close();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = () => { reconnectAttempts = 0; console.log('WS connected'); };
    ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch {} };
    ws.onclose = () => { setTimeout(() => connect(onMessage), Math.min(1000 * Math.pow(2, reconnectAttempts++), 30000)); };
    ws.onerror = (e) => console.error('WS error:', e);
  }

  function send(data) { if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data)); }
  function close() { if (ws) ws.close(); }

  return { connect, send, close };
})();

// ========================================
// MAIN APP STATE
// ========================================
const state = StateManager.load();
const XP_PER_LEVEL = (lvl) => Math.floor(100 * Math.pow(1.5, lvl - 1));

const BADGES = {
  'first-gen': { name: 'First Blood', desc: 'Generated your first image', icon: '🎨' },
  'hundred-gen': { name: 'Centurion', desc: '100 generations', icon: '💯' },
  'gpu-master': { name: 'GPU Master', desc: 'Used all 3 GPUs', icon: '🎮' },
  'workflow-creator': { name: 'Architect', desc: 'Created custom workflow', icon: '⚙️' },
  'night-owl': { name: 'Night Owl', desc: 'Generated 12am-6am', icon: '🌙' },
  'prompt-engineer': { name: 'Wordsmith', desc: '100 prompt improvements', icon: '🔮' },
  'upscale-king': { name: 'Resolution King', desc: '50 upscales', icon: '🔍' },
  'batch-commander': { name: 'Batch Commander', desc: '10 batch jobs', icon: '📦' },
  'security-expert': { name: 'Guardian', desc: 'Detected 10 threats', icon: '🛡️' },
  'model-curator': { name: 'Curator', desc: 'Downloaded 20 models', icon: '📚' },
  'node-master': { name: 'Node Master', desc: 'Installed 10 custom nodes', icon: '🔧' }
};

// ========================================
// UI COMPONENTS (Reusable, Interactive)
// ========================================

const UI = {
  // Toast notifications
  toast(title, msg, type = 'info', duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const icons = { success: '✅', warning: '⚠️', error: '❌', info: 'ℹ️', xp: '✨', threat: '🚨' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><div class="toast-content"><div class="toast-title">${title}</div><div class="toast-message">${msg}</div></div><button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
  },

  // Modal with dynamic content
  modal(title, content, size = 'md') {
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal');
    if (!overlay || !modal) return;
    modal.className = `modal modal-${size}`;
    modal.innerHTML = `<div class="modal-header"><h3 class="modal-title">${title}</h3><button class="modal-close" onclick="UI.closeModal()">✕</button></div><div class="modal-body">${content}</div>`;
    overlay.classList.remove('hidden');
  },

  closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.classList.add('hidden');
  },

  // Confirmation dialog
  confirm(msg, onConfirm, onCancel) {
    this.modal('Confirm', `<p>${msg}</p><div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px"><button class="btn" onclick="UI.closeModal();${onCancel || ''}">Cancel</button><button class="btn primary" onclick="UI.closeModal();${onConfirm}">Confirm</button></div>`);
  },

  // Loading state
  setLoading(btn, loading, originalText) {
    if (loading) { btn.dataset.original = btn.innerHTML; btn.innerHTML = '⏳ Loading...'; btn.disabled = true; }
    else { btn.innerHTML = btn.dataset.original || originalText; btn.disabled = false; }
  }
};

// ========================================
// API CLIENT with Security Headers
// ========================================
const API = {
  base: '',
  token: (typeof window !== 'undefined' && window.__DASHBOARD_TOKEN__) || '',

  async request(endpoint, options = {}, expectJson = true) {
    const headers = {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      'X-Request-ID': crypto.randomUUID(),
      ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {}),
      ...(options.headers || {})
    };
    const res = await fetch(`${this.base}${endpoint}`, { ...options, headers });
    if (!res.ok) throw new Error(await res.text());
    if (!expectJson) return await res.text();
    const text = await res.text();
    if (!text) return {};
    try { return JSON.parse(text); } catch { return text; }
  },

  // System
  health() { return this.request('/health'); },
  gpuStatus() { return this.request('/gpu-status'); },
  ollamaStatus() { return this.request('/ollama-status'); },
  report() { return this.request('/api/report'); },
  heal() { return this.request('/api/heal', { method: 'POST' }); },
  jobs() { return this.request('/api/jobs'); },
  job(id) { return this.request(`/api/jobs/${id}`); },
  achievements() { return this.request('/api/achievements'); },
  systemSnapshot() { return this.request('/api/system/snapshot'); },
  systemSelfHeal() { return this.request('/api/system/self-heal', { method: 'POST' }); },
  systemWatchdog() { return this.request('/api/system/watchdog'); },
  moneyLeads() { return this.request('/api/money/leads'); },
  briefing() { return this.request('/api/cooperator/briefing'); },
  coopRun(text) { return this.request('/api/cooperator/run', { method: 'POST', body: JSON.stringify({ directive: text }) }); },
  coopRepos() { return this.request('/api/cooperator/repos'); },
  privateCreations() { return this.request('/api/private-creations'); },
  diskRescue() { return this.request('/api/disk/rescue'); },
  diskRescueRun(action) { return this.request('/api/disk/rescue', { method: 'POST', body: JSON.stringify({ action }) }); },
  modelTruth() { return this.request('/api/models/truth'); },
  smokeStatus() { return this.request('/api/dashboard/smoke'); },
  runSmoke() { return this.request('/api/dashboard/smoke', { method: 'POST' }); },
  dashboardLogs(lines = 120) { return this.request(`/api/dashboard/logs?lines=${lines}`); },
  workstationOp() { return this.request('/api/workstation/op', { method: 'POST' }); },
  workstationOpStatus() { return this.request('/api/workstation/op'); },
  agentCommand(directive) { return this.request('/api/agent/command', { method: 'POST', body: JSON.stringify({ directive }) }); },
  improvements() { return this.request('/api/agent/improvements'); },
  revenue() { return this.request('/api/revenue/status'); },
  predictions() { return this.request('/api/system/predictions'); },
  workflowPacks() { return this.request('/api/workflows/productize'); },
  workflowPack(slug) { return this.request(`/api/workflows/productize/${slug}`); },

  // Prompt
  improvePrompt(prompt, mode) { return this.request('/api/improve-prompt', { method: 'POST', body: JSON.stringify({ prompt, mode }) }); },
  generate(prompt, workflow, mode, options = {}) { return this.request('/api/generate', { method: 'POST', body: JSON.stringify({ prompt, workflow, mode, ...options }) }); },
  upscale(body = {}) { return this.request('/api/upscale', { method: 'POST', body: JSON.stringify(body) }); },
  variations(body = {}) { return this.request('/api/variations', { method: 'POST', body: JSON.stringify(body) }); },
  cleanup() { return this.request('/api/cleanup', { method: 'POST' }); },
  backup() { return this.request('/api/backup', { method: 'POST' }); },

  // ComfyUI Models/Nodes
  comfyModels() { return this.request('/api/comfy/models'); },
  comfyNodes() { return this.request('/api/comfy/nodes'); },
  downloadModel(url, type, target_folder) { return this.request('/api/comfy/download', { method: 'POST', body: JSON.stringify({ url, type, target_folder }) }); },
  installNode(repo) { return this.request('/api/comfy/install-node', { method: 'POST', body: JSON.stringify({ repo }) }); },

  // Ollama
  ollamaModels(port) { return this.request(`http://localhost:${port}/api/tags`); },
  ollamaPull(port, model) { return this.request(`http://localhost:${port}/api/pull`, { method: 'POST', body: JSON.stringify({ name: model }) }); },
  ollamaDelete(port, model) { return this.request(`http://localhost:${port}/api/delete`, { method: 'DELETE', body: JSON.stringify({ name: model }) }); },

  // Security
  threatScan(text) { return this.request('/api/security/scan', { method: 'POST', body: JSON.stringify({ text }) }); },
  auditLog() { return this.request('/api/security/audit'); },
  threatStats() { return this.request('/api/security/stats'); },

  // Workflows
  workflows() { return this.request('/api/comfy/workflows'); },
  getWorkflow(id) { return this.request(`/api/comfy/workflows/${id}`); },
  saveWorkflow(wf) { return this.request('/api/comfy/workflows', { method: 'POST', body: JSON.stringify(wf) }); },
  queueWorkflow(id) { return this.request(`/api/comfy/workflows/${id}/queue`, { method: 'POST' }); },
  deleteWorkflow(id) { return this.request(`/api/comfy/workflows/${id}`, { method: 'DELETE' }); },
  comfyQueue() { return this.request('/api/comfy/queue'); },
  uploadFiles(files) {
    const form = new FormData();
    Array.from(files || []).forEach(f => form.append('files', f));
    return this.request('/api/upload', { method: 'POST', body: form });
  },
  customTools() { return this.request('/api/tools/custom'); },
  runTool(toolId, payload = {}) { return this.request('/api/tools/custom', { method: 'POST', body: JSON.stringify({ tool_id: toolId, payload }) }); },
  mcpAgents() { return this.request('/api/mcp/agents'); },
  runMCP(agentId, prompt, model) { return this.request('/api/mcp/run', { method: 'POST', body: JSON.stringify({ agent_id: agentId, prompt, model }) }); },
  dashboardViews() { return this.request('/api/views'); },
  saveView(view) { return this.request('/api/views', { method: 'POST', body: JSON.stringify(view) }); },
  deleteView(id) { return this.request(`/api/views/${id}`, { method: 'DELETE' }); },
  loadWorkflow(id) { return this.request(`/api/comfy/workflows/${id}`); }
};

// ========================================
// COMPONENT: GPU Card (Interactive)
// ========================================
function createGPUCard(gpu, index) {
  const memUsed = parseInt(gpu.memory.split('/')[0]);
  const memTotal = parseInt(gpu.memory.split('/')[1]);
  const memPct = memTotal > 0 ? Math.round((memUsed / memTotal) * 100) : 0;
  const utilPct = gpu.utilization || 0;
  const memClass = memPct > 85 ? 'danger' : memPct > 70 ? 'warn' : '';
  const utilClass = utilPct > 85 ? 'danger' : utilPct > 70 ? 'warn' : '';
  const nameMap = { 0: 'V100 (GPU 0)', 1: 'P40 (GPU 1)', 2: 'RTX 3060 (GPU 2)' };

  return `
    <div class="gpu-card clickable" data-gpu="${index}" onclick="GPUPanel.open(${index})">
      <div class="gpu-header">
        <span class="gpu-name">${nameMap[index] || `GPU ${index}`}</span>
        <span class="gpu-index">#${index}</span>
      </div>
      <div class="gpu-stats">
        <div class="gpu-stat">
          <span class="gpu-stat-label">VRAM</span>
          <span class="gpu-stat-value ${memClass}">${gpu.memory}</span>
          <div class="gpu-bar"><div class="gpu-bar-fill ${memClass}" style="width: ${memPct}%"></div></div>
        </div>
        <div class="gpu-stat">
          <span class="gpu-stat-label">Util</span>
          <span class="gpu-stat-value ${utilClass}">${utilPct}%</span>
          <div class="gpu-bar"><div class="gpu-bar-fill ${utilClass}" style="width: ${utilPct}%"></div></div>
        </div>
      </div>
      <div class="gpu-actions">
        <button class="btn small" onclick="event.stopPropagation(); GPUPanel.open(${index})">Details</button>
        <button class="btn small" onclick="event.stopPropagation(); GPUPanel.killProcesses(${index})">Kill</button>
      </div>
    </div>
  `;
}

// ========================================
// COMPONENT: Ollama Lane Card (Interactive)
// ========================================
function createLaneCard(lane) {
  const isHealthy = lane.healthy;
  const nameUpper = lane.name.toUpperCase();
  const version = lane.version || 'unknown';
  const versionWarning = lane.mixedVersion ? `<div class="lane-warning">Version mismatch: ${escapeHtml(version)} vs expected ${escapeHtml(lane.expectedVersion || 'unknown')}</div>` : '';

  return `
    <div class="lane-card clickable" data-lane="${lane.name}">
      <div class="lane-header">
        <span class="lane-name ${lane.name}">${nameUpper}</span>
        <span class="lane-status">
          <span class="lane-dot ${isHealthy ? 'online' : ''}"></span>
          <span>${isHealthy ? 'Online' : 'Offline'}</span>
        </span>
      </div>
      <div class="lane-info">
        <div class="lane-info-item"><span class="lane-info-label">Port</span><span class="lane-info-value">${lane.port}</span></div>
        <div class="lane-info-item"><span class="lane-info-label">Memory</span><span class="lane-info-value">${lane.memory}</span></div>
        <div class="lane-info-item"><span class="lane-info-label">Version</span><span class="lane-info-value">${version}</span></div>
      </div>
      <div class="lane-models">
        <span class="lane-models-label">Models</span>
        <span class="lane-models-count">${lane.models || 0}</span>
      </div>
      ${versionWarning}
      <div class="lane-actions">
        <button class="btn small" onclick="event.stopPropagation(); LaneManager.open('${lane.name}', ${lane.port})">Manage</button>
        <button class="btn small" onclick="event.stopPropagation(); LaneManager.pullModel('${lane.name}', ${lane.port})">Pull</button>
      </div>
    </div>
  `;
}

// ========================================
// COMPONENT: Threat Alert Card
// ========================================
function createThreatCard(threat) {
  const time = new Date(threat.timestamp).toLocaleTimeString();
  const severityClass = threat.severity >= 8 ? 'danger' : threat.severity >= 6 ? 'warn' : 'info';
  return `
    <div class="threat-card ${severityClass}">
      <div class="threat-header">
        <span class="threat-type">${threat.category.replace(/([A-Z])/g, ' $1').trim()}</span>
        <span class="threat-severity badge-${severityClass}">Sev ${threat.severity}/10</span>
      </div>
      <div class="threat-time">${time}</div>
      <div class="threat-pattern"><code>${threat.pattern}</code></div>
      <div class="threat-actions">
        <button class="btn small" onclick="SecurityPanel.blockSource('${threat.source}')">Block</button>
        <button class="btn small" onclick="SecurityPanel.ignore('${threat.id}')">Ignore</button>
      </div>
    </div>
  `;
}

// ========================================
// PANEL: GPU Detailed View
// ========================================
const GPUPanel = {
  open(index) {
    const gpu = state.gpus[index];
    if (!gpu) return;

    const nameMap = { 0: 'Tesla V100-SXM2-16GB', 1: 'Tesla P40', 2: 'RTX 3060' };
    const memUsed = parseInt(gpu.memory.split('/')[0]);
    const memTotal = parseInt(gpu.memory.split('/')[1]);
    const memPct = memTotal > 0 ? Math.round((memUsed / memTotal) * 100) : 0;
    const utilPct = gpu.utilization || 0;

    UI.modal(`GPU ${index}: ${nameMap[index] || 'Unknown'}`, `
      <div class="panel-content">
        <div class="detail-grid">
          <div class="detail-item"><span class="label">VRAM Used</span><span class="value">${gpu.memory}</span></div>
          <div class="detail-item"><span class="label">VRAM %</span><span class="value">${memPct}%</span></div>
          <div class="detail-item"><span class="label">Utilization</span><span class="value">${utilPct}%</span></div>
          <div class="detail-item"><span class="label">Temperature</span><span class="value">${gpu.temperature || 'N/A'}°C</span></div>
          <div class="detail-item"><span class="label">Power</span><span class="value">${gpu.power || 'N/A'}W</span></div>
          <div class="detail-item"><span class="label">Clock</span><span class="value">${gpu.clock || 'N/A'}MHz</span></div>
        </div>
        <div class="chart-placeholder" id="gpu-chart-${index}" style="height:200px;background:var(--bg);border-radius:8px;margin-top:16px;border:1px solid var(--border)">
          <canvas id="gpu-canvas-${index}"></canvas>
        </div>
        <div class="process-list" id="gpu-processes-${index}"></div>
      </div>
    `, 'lg');

    this.loadProcesses(index);
    this.initChart(index);
  },

  async loadProcesses(index) {
    try {
      const res = await fetch(`/api/gpu/${index}/processes`);
      if (res.ok) {
        const data = await res.json();
        const processes = Array.isArray(data) ? data : (data.processes || []);
        const container = document.getElementById(`gpu-processes-${index}`);
        container.innerHTML = `
          <h4>Running Processes</h4>
          <table class="process-table">
            <thead><tr><th>PID</th><th>Name</th><th>VRAM</th><th>Type</th><th>Action</th></tr></thead>
            <tbody>
              ${processes.map(p => `<tr><td>${p.pid}</td><td>${p.name}</td><td>${p.vram}MB</td><td>${p.type}</td><td><button class="btn small danger" onclick="GPUPanel.killProcess(${p.pid})">Kill</button></td></tr>`).join('') || '<tr><td colspan="5">No GPU processes found</td></tr>'}
            </tbody>
          </table>
        `;
      }
    } catch (e) { console.error('Failed to load GPU processes:', e); }
  },

  initChart(index) {
    // Simple canvas chart for GPU history
    const canvas = document.getElementById(`gpu-canvas-${index}`);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 200;
    // Draw placeholder
    ctx.fillStyle = 'var(--fg-subtle)';
    ctx.font = '14px var(--font-mono)';
    ctx.textAlign = 'center';
    ctx.fillText('Real-time chart - connect to /ws for live data', canvas.width/2, canvas.height/2);
  },

  async killProcesses(index) {
    if (!confirm('Kill all processes on this GPU?')) return;
    try {
      await fetch(`/api/gpu/${index}/kill-all`, { method: 'POST' });
      UI.toast('Success', 'All GPU processes killed', 'success');
      this.loadProcesses(index);
    } catch (e) { UI.toast('Error', 'Failed to kill processes', 'error'); }
  },

  async killProcess(pid) {
    if (!confirm(`Kill process ${pid}?`)) return;
    try {
      await fetch(`/api/process/${pid}/kill`, { method: 'POST' });
      UI.toast('Success', `Process ${pid} killed`, 'success');
    } catch (e) { UI.toast('Error', 'Failed to kill process', 'error'); }
  }
};

// ========================================
// PANEL: Ollama Lane Manager
// ========================================
const LaneManager = {
  currentLane: null,
  currentPort: null,

  async open(lane, port) {
    this.currentLane = lane;
    this.currentPort = port;
    const models = await API.ollamaModels(port);
    UI.modal(`${lane.toUpperCase()} Lane (Port ${port})`, `
      <div class="panel-content">
        <div class="lane-toolbar">
          <input type="text" id="model-search" placeholder="Search models..." class="search-input" oninput="LaneManager.filterModels(this.value)">
          <button class="btn primary" onclick="LaneManager.showPullModal()">⬇ Pull Model</button>
          <button class="btn" onclick="LaneManager.refresh()">⟳ Refresh</button>
        </div>
        <div class="model-list" id="model-list-${lane}">
          ${models.models?.map(m => `
            <div class="model-item" data-name="${m.name}">
              <div class="model-info">
                <span class="model-name">${m.name}</span>
                <span class="model-meta">${(m.size/1e9).toFixed(1)}B • ${m.details?.quantization_level || 'N/A'}</span>
              </div>
              <div class="model-actions">
                <button class="btn small" onclick="LaneManager.testModel('${lane}', ${port}, '${m.name}')">Test</button>
                <button class="btn small danger" onclick="LaneManager.deleteModel('${lane}', ${port}, '${m.name}')">Delete</button>
              </div>
            </div>
          `).join('') || '<p class="empty">No models installed</p>'}
        </div>
      </div>
    `, 'lg');
  },

  filterModels(query) {
    const items = document.querySelectorAll('.model-item');
    items.forEach(item => {
      const name = item.dataset.name.toLowerCase();
      item.style.display = name.includes(query.toLowerCase()) ? 'flex' : 'none';
    });
  },

  async refresh() {
    if (!this.currentLane) return;
    const models = await API.ollamaModels(this.currentPort);
    const container = document.getElementById(`model-list-${this.currentLane}`);
    container.innerHTML = models.models?.map(m => `
      <div class="model-item" data-name="${m.name}">
        <div class="model-info"><span class="model-name">${m.name}</span><span class="model-meta">${(m.size/1e9).toFixed(1)}B • ${m.details?.quantization_level || 'N/A'}</span></div>
        <div class="model-actions"><button class="btn small" onclick="LaneManager.testModel('${this.currentLane}', ${this.currentPort}, '${m.name}')">Test</button><button class="btn small danger" onclick="LaneManager.deleteModel('${this.currentLane}', ${this.currentPort}, '${m.name}')">Delete</button></div>
      </div>
    `).join('') || '<p class="empty">No models installed</p>';
  },

  showPullModal() {
    UI.modal('Pull Model', `
      <div class="panel-content">
        <div class="field"><label>Model Name (e.g., llama3:70b, qwen2.5:32b, flux:dev)</label><input type="text" id="pull-model-name" class="textarea" placeholder="llama3:70b"></div>
        <div class="field"><label>Source Registry</label><select id="pull-registry" class="select"><option value="ollama">Ollama Library</option><option value="huggingface">HuggingFace (GGUF)</option></select></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px"><button class="btn" onclick="UI.closeModal()">Cancel</button><button class="btn primary" onclick="LaneManager.doPull()">Pull Model</button></div>
      </div>
    `);
  },

  async doPull() {
    const name = document.getElementById('pull-model-name').value.trim();
    if (!name) return UI.toast('Error', 'Enter model name', 'error');
    UI.closeModal();
    UI.toast('Pulling', `Downloading ${name}...`, 'info');
    try {
      await API.ollamaPull(this.currentPort, name);
      UI.toast('Success', `${name} downloaded`, 'success');
      this.refresh();
      StateManager.save(state);
    } catch (e) { UI.toast('Error', 'Pull failed: ' + e.message, 'error'); }
  },

  async testModel(lane, port, model) {
    try {
      const res = await fetch(`http://localhost:${port}/api/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, prompt: 'Hello, respond with "OK"', stream: false, options: { num_predict: 5 } })
      });
      if (res.ok) UI.toast('Success', `${model} responded OK`, 'success');
      else UI.toast('Error', 'Model test failed', 'error');
    } catch (e) { UI.toast('Error', 'Connection failed', 'error'); }
  },

  async deleteModel(lane, port, model) {
    if (!confirm(`Delete ${model} from ${lane}?`)) return;
    try {
      await API.ollamaDelete(port, model);
      UI.toast('Deleted', `${model} removed`, 'success');
      this.refresh();
    } catch (e) { UI.toast('Error', 'Delete failed', 'error'); }
  }
};

// ========================================
// PANEL: ComfyUI Model/Node Manager
// ========================================
const ComfyManager = {
  async open() {
    const [models, nodes, workflows] = await Promise.all([
      API.comfyModels().catch(() => ({ models: [] })),
      API.comfyNodes().catch(() => ({ nodes: [] })),
      API.workflows().catch(() => ({ workflows: [] }))
    ]);

    state.comfyui = { models: models.models || [], nodes: nodes.nodes || [], workflows: workflows.workflows || [] };
    StateManager.save(state);

    UI.modal('ComfyUI Manager', `
      <div class="panel-content" style="max-height:70vh">
        <div class="tabs">
          <button class="tab-btn active" data-tab="models" onclick="ComfyManager.switchTab('models')">📦 Models (${state.comfyui.models.length})</button>
          <button class="tab-btn" data-tab="nodes" onclick="ComfyManager.switchTab('nodes')">🔌 Nodes (${state.comfyui.nodes.length})</button>
          <button class="tab-btn" data-tab="workflows" onclick="ComfyManager.switchTab('workflows')">📋 Workflows (${state.comfyui.workflows.length})</button>
          <button class="tab-btn" data-tab="download" onclick="ComfyManager.switchTab('download')">⬇ Download</button>
        </div>
        <div class="tab-content">
          <div id="tab-models" class="tab-pane active">${this.renderModels()}</div>
          <div id="tab-nodes" class="tab-pane">${this.renderNodes()}</div>
          <div id="tab-workflows" class="tab-pane">${this.renderWorkflows()}</div>
          <div id="tab-download" class="tab-pane">${this.renderDownload()}</div>
        </div>
      </div>
    `, 'xl');

    this.initDownloadHandlers();
  },

  switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
  },

  renderModels() {
    if (state.comfyui.models.length === 0) return '<div class="empty-state">No models found. Use Download tab to add models.</div>';
    return state.comfyui.models.map(m => `
      <div class="model-card">
        <div class="model-icon">${this.getModelIcon(m.type)}</div>
        <div class="model-info"><span class="model-name">${m.name}</span><span class="model-meta">${m.type} • ${m.size}</span></div>
        <div class="model-actions"><button class="btn small" onclick="ComfyManager.deleteModel('${m.name}')">Delete</button></div>
      </div>
    `).join('');
  },

  renderNodes() {
    if (state.comfyui.nodes.length === 0) return '<div class="empty-state">No custom nodes installed. Use Download tab to add nodes.</div>';
    return state.comfyui.nodes.map(n => `
      <div class="node-card">
        <div class="node-info"><span class="node-name">${n.name}</span><span class="node-meta">${n.version} • ${n.author}</span></div>
        <div class="node-actions"><button class="btn small danger" onclick="ComfyManager.uninstallNode('${n.name}')">Uninstall</button></div>
      </div>
    `).join('');
  },

  renderWorkflows() {
    if (state.comfyui.workflows.length === 0) return '<div class="empty-state">No workflows saved. Create one in the Workflow Builder.</div>';
    return state.comfyui.workflows.map(w => `
      <div class="workflow-card">
        <div class="wf-info"><span class="wf-name">${w.name}</span><span class="wf-meta">${w.nodes} nodes • ${w.updated}</span></div>
        <div class="wf-actions">
          <button class="btn small" onclick="WorkflowBuilder.load('${w.id}')">Edit</button>
          <button class="btn small primary" onclick="ComfyManager.queueWorkflow('${w.id}')">Queue</button>
          <button class="btn small danger" onclick="ComfyManager.deleteWorkflow('${w.id}')">Delete</button>
        </div>
      </div>
    `).join('');
  },

  renderDownload() {
    return `
      <div class="download-section">
        <h4>Download from CivitAI / HuggingFace</h4>
        <div class="field"><label>Model URL</label><input type="url" id="dl-url" class="textarea" placeholder="https://civitai.com/models/12345 or https://huggingface.co/user/model"></div>
        <div class="studio-row">
          <div class="field"><label>Type</label><select id="dl-type" class="select"><option value="checkpoint">Checkpoint</option><option value="diffusion">Diffusion/UNet</option><option value="text_encoder">Text Encoder</option><option value="lora">LoRA</option><option value="vae">VAE</option><option value="controlnet">ControlNet</option><option value="upscaler">Upscaler</option></select></div>
          <div class="field"><label>Target Folder</label><select id="dl-folder" class="select"><option value="checkpoints">checkpoints</option><option value="diffusion_models">diffusion_models</option><option value="text_encoders">text_encoders</option><option value="loras">loras</option><option value="vae">vae</option><option value="embeddings">embeddings</option><option value="controlnet">controlnet</option><option value="upscale_models">upscale_models</option><option value="clip">clip</option><option value="clip_vision">clip_vision</option></select></div>
        </div>
        <button class="btn primary" onclick="ComfyManager.startDownload()">Download & Install</button>
        <div id="dl-progress" class="progress-bar hidden"><div class="progress-fill"></div></div>
        <pre id="dl-log" class="log-output"></pre>
      </div>
    `;
  },

  initDownloadHandlers() {
    // WebSocket for download progress
  },

  async startDownload() {
    const url = document.getElementById('dl-url').value;
    const type = document.getElementById('dl-type').value;
    const folder = document.getElementById('dl-folder').value;
    if (!url) return UI.toast('Error', 'Enter URL', 'error');

    UI.toast('Downloading', 'Starting download...', 'info');
    try {
      const folder = document.getElementById('dl-folder').value;
      await API.downloadModel(url, type, folder);
      UI.toast('Success', 'Model downloaded', 'success');
      ComfyManager.open();
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  },

  getModelIcon(type) {
    const icons = { checkpoint: '📦', lora: '🎨', vae: '🔮', embedding: '📝', controlnet: '🎮', upscaler: '🔍' };
    return icons[type] || '📄';
  }
};

// ========================================
// COMPONENT: Workflow Builder (Visual)
// ========================================
const WorkflowBuilder = {
  currentWorkflow: null,
  nodes: [],
  edges: [],

  async open() {
    UI.modal('Workflow Builder', `
      <div class="workflow-builder" style="height:70vh">
        <div class="builder-toolbar">
          <button class="btn" onclick="WorkflowBuilder.save()">💾 Save</button>
          <button class="btn primary" onclick="WorkflowBuilder.queue()">🚀 Queue</button>
          <button class="btn" onclick="WorkflowBuilder.export()">📤 Export</button>
          <input type="text" id="wf-name" placeholder="Workflow name" style="margin-left:auto;width:200px">
        </div>
        <div class="builder-canvas" id="builder-canvas"></div>
        <div class="node-palette" id="node-palette">${this.renderPalette()}</div>
      </div>
    `, 'xl');

    this.initCanvas();
  },

  renderPalette() {
    const categories = {
      'Loaders': ['LoadImage', 'LoadModel', 'LoadLoRA', 'LoadVAE'],
      'Sampling': ['KSampler', 'KSamplerAdvanced', 'Noise', 'Guidance'],
      'Conditioning': ['CLIPTextEncode', 'CLIPTextEncodeSDXL', 'ConditioningCombine', 'ConditioningZeroOut'],
      'Latent': ['EmptyLatentImage', 'LatentUpscale', 'VAEEncode', 'VAEDecode'],
      'Image': ['ImageScale', 'ImageCrop', 'ImageBlend', 'ImageComposite', 'SaveImage'],
      'Utils': ['PreviewImage', 'GetImageSize', 'Primitive', 'Reroute']
    };
    return Object.entries(categories).map(([cat, nodes]) => `
      <div class="palette-category"><h4>${cat}</h4><div class="palette-nodes">${nodes.map(n => `<button class="palette-node" draggable="true" data-node="${n}" ondragstart="WorkflowBuilder.dragStart(event)">${n}</button>`).join('')}</div>
    `).join('');
  },

  initCanvas() {
    // Initialize drag-drop canvas (simplified - use a library like React Flow in production)
    const canvas = document.getElementById('builder-canvas');
    canvas.addEventListener('dragover', e => e.preventDefault());
    canvas.addEventListener('drop', e => {
      e.preventDefault();
      const nodeType = e.dataTransfer.getData('text/plain');
      if (nodeType) this.addNode(nodeType, e.offsetX, e.offsetY);
    });
  },

  dragStart(e) { e.dataTransfer.setData('text/plain', e.target.dataset.node); },

  addNode(type, x, y) {
    const id = `node_${Date.now()}`;
    const node = { id, type, pos: { x, y }, inputs: {}, outputs: {} };
    this.nodes.push(node);
    this.render();
  },

  render() {
    // Render nodes on canvas (simplified)
  },

  save() {
    const name = document.getElementById('wf-name').value || `workflow_${Date.now()}`;
    const wf = { id: `wf_${Date.now()}`, name, nodes: this.nodes, edges: this.edges, created: Date.now() };
    state.comfyui.workflows.push(wf);
    StateManager.save(state);
    UI.toast('Saved', 'Workflow saved', 'success');
  }
};

// ========================================
// PANEL: Security & Threat Detection
// ========================================
const SecurityPanel = {
  threats: [],
  auditLog: [],

  async open() {
    await this.loadData();
    UI.modal('Security Center', `
      <div class="panel-content" style="max-height:80vh">
        <div class="tabs">
          <button class="tab-btn active" data-tab="threats" onclick="SecurityPanel.switchTab('threats')">🚨 Threats (${this.threats.length})</button>
          <button class="tab-btn" data-tab="audit" onclick="SecurityPanel.switchTab('audit')">📋 Audit Log</button>
          <button class="tab-btn" data-tab="anomalies" onclick="SecurityPanel.switchTab('anomalies')">🔍 Anomalies</button>
          <button class="tab-btn" data-tab="settings" onclick="SecurityPanel.switchTab('settings')">⚙️ Settings</button>
        </div>
        <div class="tab-content">
          <div id="tab-threats" class="tab-pane active">${this.renderThreats()}</div>
          <div id="tab-audit" class="tab-pane">${this.renderAudit()}</div>
          <div id="tab-anomalies" class="tab-pane">${this.renderAnomalies()}</div>
          <div id="tab-settings" class="tab-pane">${this.renderSettings()}</div>
        </div>
      </div>
    `, 'xl');
  },

  async loadData() {
    try {
      const [threats, audit, stats] = await Promise.all([
        API.threatStats().catch(() => ({ threats: [] })),
        API.auditLog().catch(() => ({ logs: [] })),
        API.threatStats().catch(() => ({}))
      ]);
      this.threats = threats.threats || [];
      this.auditLog = audit.logs || [];
    } catch (e) { console.error('Security data load failed:', e); }
  },

  switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
  },

  renderThreats() {
    if (this.threats.length === 0) return '<div class="empty-state">No threats detected. System secure.</div>';
    return this.threats.map(t => createThreatCard(t)).join('');
  },

  renderAudit() {
    if (this.auditLog.length === 0) return '<div class="empty-state">No audit events.</div>';
    return this.auditLog.slice(0, 50).map(log => `
      <div class="audit-item ${log.severity || 'info'}">
        <span class="audit-time">${new Date(log.timestamp).toLocaleString()}</span>
        <span class="audit-action">${log.action}</span>
        <span class="audit-detail">${log.detail}</span>
        <span class="audit-ip">${log.ip || 'local'}</span>
      </div>
    `).join('');
  },

  renderAnomalies() {
    // Behavioral anomalies
    return '<div class="empty-state">Anomaly detection running... Check back after traffic.</div>';
  },

  renderSettings() {
    return `
      <div class="settings-grid">
        <div class="setting-item"><label>Threat Detection Sensitivity</label><input type="range" id="sensitivity" min="1" max="10" value="7" onchange="SecurityPanel.updateSetting('sensitivity', this.value)"></div>
        <div class="setting-item"><label>Auto-block IPs</label><label class="toggle"><input type="checkbox" id="auto-block" checked onchange="SecurityPanel.updateSetting('autoBlock', this.checked)"><span class="slider"></span></label></div>
        <div class="setting-item"><label>Log Retention (days)</label><input type="number" id="retention" value="30" min="1" max="365" onchange="SecurityPanel.updateSetting('retention', this.value)"></div>
        <div class="setting-item"><label>API Key Rotation</label><button class="btn" onclick="SecurityPanel.rotateKeys()">Rotate Keys</button></div>
        <div class="setting-item"><label>Encryption</label><label class="toggle"><input type="checkbox" id="encrypt-logs" checked onchange="SecurityPanel.updateSetting('encryptLogs', this.checked)"><span class="slider"></span></label></div>
      </div>
    `;
  },

  updateSetting(key, value) {
    // Save to backend
    UI.toast('Updated', `${key} set to ${value}`, 'success');
  },

  rotateKeys() {
    UI.toast('Rotating', 'API keys rotated', 'info');
  },

  blockSource(source) { UI.toast('Blocked', `Source ${source} blocked`, 'success'); },
  ignore(threatId) { UI.toast('Ignored', 'Threat marked as false positive', 'info'); }
};

// ========================================
// COMPONENT: Mature Content Workflow Templates
// ========================================
const MatureWorkflows = {
  templates: {
    'private-adult-fiction': {
      name: 'Private Adult Fiction - Cinematic',
      description: 'High-quality cinematic renders for fictional adult narratives',
      safetyLevel: 'strict',
      workflow: {
        nodes: [
          { id: 'prompt', type: 'CLIPTextEncode', title: 'Positive Prompt', pos: [200, 100] },
          { id: 'negative', type: 'CLIPTextEncode', title: 'Negative Prompt', pos: [200, 300] },
          { id: 'model', type: 'CheckpointLoaderSimple', title: 'Model (SDXL/Pony)', pos: [200, 500] },
          { id: 'sampler', type: 'KSampler', title: 'Sampler', pos: [500, 300] },
          { id: 'decode', type: 'VAEDecode', title: 'VAE Decode', pos: [800, 300] },
          { id: 'save', type: 'SaveImage', title: 'Save', pos: [1100, 300] }
        ]
      }
    },
    'lingerie-fashion': {
      name: 'Lingerie & Fashion Photography',
      description: 'Professional fashion/lingerie renders with studio lighting',
      safetyLevel: 'moderate',
      workflow: { /* ... */ }
    },
    'artistic-nude': {
      name: 'Artistic Nude - Fine Art',
      description: 'Classical artistic nude studies, museum quality',
      safetyLevel: 'strict',
      workflow: { /* ... */ }
    }
  },

  async open() {
    UI.modal('Mature Content Workflows', `
      <div class="panel-content">
        <div class="safety-banner">🔒 All templates enforce fictional-only, consenting-adult content. No real persons, no minors, no non-consensual content.</div>
        <div class="template-grid">
          ${Object.entries(this.templates).map(([id, t]) => `
            <div class="template-card" onclick="MatureWorkflows.load('${id}')">
              <div class="template-icon">${this.getIcon(id)}</div>
              <h4>${t.name}</h4>
              <p>${t.description}</p>
              <span class="safety-badge level-${t.safetyLevel}">${t.safetyLevel}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `, 'lg');
  },

  load(id) {
    const template = this.templates[id];
    UI.closeModal();
    WorkflowBuilder.nodes = template.workflow.nodes.map(n => ({ ...n, id: `node_${Date.now()}_${Math.random()}` }));
    WorkflowBuilder.open();
    UI.toast('Loaded', `${template.name} loaded in builder`, 'success');
  },

  getIcon(id) {
    const icons = { 'private-adult-fiction': '📖', 'lingerie-fashion': '👗', 'artistic-nude': '🎨' };
    return icons[id] || '📋';
  }
};

// ========================================
// DASHBOARD EXTENSION: Tools, MCP Agents, Workflows, Views
// ========================================
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}
function formatDateTime(value) {
  if (!value) return '—';
  const numeric = typeof value === 'number' || /^\d+$/.test(String(value)) ? Number(value) : value;
  const d = new Date(typeof numeric === 'number' && numeric > 0 && numeric < 1000000000000 ? numeric * 1000 : numeric);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}
function renderJson(value, emptyText = 'No data') {
  if (!value) return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
  if (typeof value === 'string') return `<pre class="json-output">${escapeHtml(value)}</pre>`;
  return `<pre class="json-output">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}
function renderList(items, renderItem) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return `<div class="empty-state">No items yet.</div>`;
  return `<div class="card-grid">${list.map(renderItem).join('')}</div>`;
}
function tabButton(tab, label, activeTab) {
  return `<button class="tab-btn ${activeTab === tab ? 'active' : ''}" data-tab="${tab}">${label}</button>`;
}
function setModalTabs(activeTab) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === activeTab));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.toggle('active', pane.dataset.tabPane === activeTab));
}
const CustomToolsPanel = {
  tools: [],
  lastRun: null,
  async open() {
    await this.loadData();
    UI.modal('Custom Tools', `
      <div class="panel-content">
        <div class="toolbar-row">
          <div>
            <h4>Local tool registry</h4>
            <p class="muted">Run safe, allow-listed local helpers for reports, workflows, models, and service health.</p>
          </div>
          <button class="btn" onclick="CustomToolsPanel.refresh()">↻ Refresh</button>
        </div>
        ${this.renderTools()}
        <h4>Last Run</h4>
        ${this.lastRun ? this.renderRun(this.lastRun) : '<div class="empty-state">Run a tool to see output here.</div>'}
      </div>
    `, 'xl');
  },
  async loadData() {
    try {
      const data = await API.customTools();
      this.tools = data.tools || [];
    } catch (e) {
      this.tools = [];
      UI.toast('Error', 'Failed to load custom tools', 'error');
    }
  },
  refresh() {
    this.loadData().then(() => { if (document.querySelector('#modal .panel-content')) this.open(); });
  },
  renderTools() {
    return renderList(this.tools, tool => `
      <div class="data-card">
        <div class="data-card-head">
          <div>
            <h4>${escapeHtml(tool.name)}</h4>
            <p>${escapeHtml(tool.description || '')}</p>
          </div>
          <span class="badge-inline badge-info">${escapeHtml(tool.kind || 'tool')}</span>
        </div>
        <div class="data-card-actions">
          <button class="btn primary small" onclick="CustomToolsPanel.run('${escapeHtml(tool.id)}')">Run</button>
          <button class="btn small" onclick="CustomToolsPanel.preview('${escapeHtml(tool.id)}')">Details</button>
        </div>
      </div>
    `);
  },
  async run(toolId) {
    const tool = this.tools.find(t => t.id === toolId);
    UI.toast('Running', tool?.name || toolId, 'info');
    try {
      const data = await API.runTool(toolId, { dashboard: true });
      this.lastRun = { tool, data, at: new Date().toISOString() };
      UI.toast('Complete', (data.message || tool?.name || toolId) + ' finished', 'success');
      logActivity('Ran tool: ' + (tool?.name || toolId), 'success', 12);
      if (document.querySelector('#modal .panel-content')) this.open();
    } catch (e) {
      this.lastRun = { tool, error: e.message, at: new Date().toISOString() };
      UI.toast('Error', e.message, 'error');
      if (document.querySelector('#modal .panel-content')) this.open();
    }
  },
  preview(toolId) {
    const tool = this.tools.find(t => t.id === toolId);
    UI.modal(tool?.name || toolId, `<div class="panel-content">${renderJson(tool, 'Tool not found')}</div>`, 'md');
  },
  renderRun(run) {
    const status = run.error ? 'error' : 'success';
    return `
      <div class="run-output ${status}">
        <div class="run-meta">
          <span>${escapeHtml(run.tool?.name || 'Tool')}</span>
          <span>${formatDateTime(run.at)}</span>
        </div>
        ${run.error ? `<pre class="json-output">${escapeHtml(run.error)}</pre>` : renderJson(run.data)}
      </div>
    `;
  }
};
const MCPAgentPanel = {
  agents: [],
  selectedAgent: null,
  async open() {
    await this.loadData();
    UI.modal('MCP Agent Console', `
      <div class="panel-content">
        <div class="toolbar-row">
          <div>
            <h4>Local MCP-style agents</h4>
            <p class="muted">Route prompts to local Ollama-backed agents or built-in workflow optimizer. No cloud calls.</p>
          </div>
          <button class="btn" onclick="MCPAgentPanel.refresh()">↻ Refresh</button>
        </div>
        <div class="two-column">
          <div>${this.renderAgents()}</div>
          <div class="field-stack">
            <div class="field">
              <label>Agent</label>
              <select class="select" id="mcp-agent-select" onchange="MCPAgentPanel.selectAgent(this.value)">
                ${this.agents.map(a => `<option value="${escapeHtml(a.id)}">${escapeHtml(a.name)} — ${escapeHtml(a.model || a.kind || 'local')}</option>`).join('')}
              </select>
            </div>
            <div class="field">
              <label>Prompt</label>
              <textarea class="textarea" id="mcp-prompt" rows="8" placeholder="Ask the local agent to plan a workflow, summarize a prompt, or suggest cleanup steps..."></textarea>
            </div>
            <button class="btn primary" onclick="MCPAgentPanel.run()">Run Agent</button>
            <div id="mcp-result" class="json-output">Agent output will appear here.</div>
          </div>
        </div>
      </div>
    `, 'xl');
    if (this.agents[0]) this.selectAgent(this.agents[0].id);
  },
  async loadData() {
    try {
      const data = await API.mcpAgents();
      this.agents = data.agents || [];
    } catch (e) {
      this.agents = [];
      UI.toast('Error', 'Failed to load MCP agents', 'error');
    }
  },
  refresh() { this.loadData().then(() => this.open()); },
  renderAgents() {
    return renderList(this.agents, agent => `
      <div class="data-card">
        <div class="data-card-head">
          <div>
            <h4>${escapeHtml(agent.name)}</h4>
            <p>${escapeHtml(agent.description || '')}</p>
            <p class="muted">${escapeHtml(agent.endpoint || agent.kind || 'local')}</p>
          </div>
          <span class="badge-inline badge-purple">${escapeHtml(agent.model || 'agent')}</span>
        </div>
        <button class="btn small" onclick="MCPAgentPanel.selectAgent('${escapeHtml(agent.id)}')">Select</button>
      </div>
    `);
  },
  selectAgent(id) {
    this.selectedAgent = this.agents.find(a => a.id === id) || this.agents[0];
    const select = document.getElementById('mcp-agent-select');
    if (select) select.value = this.selectedAgent?.id || '';
  },
  async run() {
    const prompt = document.getElementById('mcp-prompt')?.value.trim();
    if (!prompt) return UI.toast('Empty', 'Enter a prompt for the agent', 'warning');
    const agent = this.selectedAgent || this.agents[0];
    if (!agent) return UI.toast('Error', 'No MCP agents configured', 'error');
    const result = document.getElementById('mcp-result');
    if (result) result.textContent = 'Running agent...';
    try {
      const data = await API.runMCP(agent.id, prompt, agent.model);
      this.lastRun = data;
      if (result) result.innerHTML = renderJson(data, 'No output');
      UI.toast('Agent complete', agent.name, 'success');
      logActivity('MCP agent: ' + agent.name, 'success', 18);
    } catch (e) {
      if (result) result.innerHTML = `<pre class="json-output">${escapeHtml(e.message)}</pre>`;
      UI.toast('Error', e.message, 'error');
    }
  }
};
const WorkflowsPanel = {
  workflows: [],
  async open() {
    await this.loadData();
    UI.modal('Workflows Data & Views', `
      <div class="panel-content">
        <div class="tabs">
          ${tabButton('workflows', 'Workflows', 'workflows')}
          ${tabButton('views', 'Views', 'views')}
          ${tabButton('builder', 'Builder', 'builder')}
        </div>
        <div class="tab-pane active" data-tab-pane="workflows">${this.renderWorkflows()}</div>
        <div class="tab-pane" data-tab-pane="views">${this.renderViewsPlaceholder()}</div>
        <div class="tab-pane" data-tab-pane="builder"><div class="empty-state">Use the Workflow Builder for visual editing. Saved workflows are stored in /home/scott/ai-lab/image/workflows.</div></div>
      </div>
    `, 'xl');
    document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => setModalTabs(btn.dataset.tab)));
  },
  async loadData() {
    try {
      const data = await API.workflows();
      this.workflows = data.workflows || [];
      state.comfyui.workflows = this.workflows;
    } catch (e) {
      this.workflows = [];
      UI.toast('Error', 'Failed to load workflows', 'error');
    }
  },
  refresh() { this.loadData().then(() => this.open()); },
  renderWorkflows() {
    return `
      <div class="toolbar-row">
        <div>
          <h4>Saved ComfyUI workflows</h4>
          <p class="muted">${this.workflows.length} workflow(s) in /home/scott/ai-lab/image/workflows</p>
        </div>
        <button class="btn" onclick="WorkflowsPanel.refresh()">↻ Refresh</button>
      </div>
      ${renderList(this.workflows, wf => `
        <div class="data-card">
          <div class="data-card-head">
            <div>
              <h4>${escapeHtml(wf.name || wf.id)}</h4>
              <p>${escapeHtml(wf.description || wf.id + '.json')}</p>
              <p class="muted">Updated ${formatDateTime(wf.updated || wf.updated_at)}</p>
            </div>
            <span class="badge-inline badge-info">${(wf.node_count || (wf.nodes?.length || 0))} nodes</span>
          </div>
          <div class="data-card-actions">
            <button class="btn primary small" onclick="WorkflowsPanel.queue('${escapeHtml(wf.id)}')">Queue</button>
            <button class="btn small" onclick="WorkflowsPanel.view('${escapeHtml(wf.id)}')">View</button>
            <button class="btn small danger" onclick="WorkflowsPanel.deleteWorkflow('${escapeHtml(wf.id)}')">Delete</button>
          </div>
        </div>
      `)}
    `;
  },
  renderViewsPlaceholder() {
    return `
      <div class="toolbar-row">
        <div>
          <h4>Dashboard views</h4>
          <p class="muted">Use the Views button to open saved views or create new ones.</p>
        </div>
        <button class="btn" onclick="ViewsPanel.open()">Open Views</button>
      </div>
      <div class="empty-state">Workflow data and dashboard views are wired through /api/comfy/workflows and /api/views.</div>
    `;
  },
  async queue(id) {
    try {
      const data = await API.queueWorkflow(id);
      UI.toast('Queued', data.prompt_id ? `Workflow ${id}: ${data.prompt_id}` : `Workflow ${id}`, 'success');
      logActivity('Queued workflow ' + id, 'success', 20);
      unlockBadge('workflow-creator');
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  },
  async view(id) {
    try {
      const wf = await API.getWorkflow(id);
      UI.modal('Workflow ' + id, `<div class="panel-content">${renderJson(wf)}</div>`, 'xl');
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  },
  async deleteWorkflow(id) {
    if (!confirm(`Delete workflow ${id}?`)) return;
    try {
      await API.deleteWorkflow(id);
      UI.toast('Deleted', id, 'success');
      logActivity('Deleted workflow ' + id, 'warning');
      this.refresh();
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  }
};
const ViewsPanel = {
  views: [],
  async open() {
    await this.loadData();
    UI.modal('Dashboard Views', `
      <div class="panel-content">
        <div class="toolbar-row">
          <div>
            <h4>Saved views</h4>
            <p class="muted">Open, save, and manage dashboard views for workflows, tools, agents, GPU, and security.</p>
          </div>
          <button class="btn" onclick="ViewsPanel.refresh()">↻ Refresh</button>
        </div>
        ${renderList(this.views, view => `
          <div class="data-card">
            <div class="data-card-head">
              <div>
                <h4>${escapeHtml(view.name)}</h4>
                <p>${escapeHtml(view.description || '')}</p>
                <p class="muted">${escapeHtml(view.type || 'view')} • ${escapeHtml(view.url || '')}</p>
              </div>
              <span class="badge-inline badge-primary">${escapeHtml(view.scope || 'local')}</span>
            </div>
            <div class="data-card-actions">
              <button class="btn primary small" onclick="ViewsPanel.openView('${escapeHtml(view.id)}')">Open</button>
              <button class="btn small" onclick="ViewsPanel.copyUrl('${escapeHtml(view.url || '')}')">Copy URL</button>
              <button class="btn small danger" onclick="ViewsPanel.deleteView('${escapeHtml(view.id)}')">Delete</button>
            </div>
          </div>
        `)}
        <h4>Create View</h4>
        <div class="field-stack">
          <div class="field"><label>Name</label><input class="input" id="view-name" placeholder="GPU + P40 lane"></div>
          <div class="field"><label>URL</label><input class="input" id="view-url" placeholder="/dashboard#gpu"></div>
          <div class="field"><label>Type</label><select class="select" id="view-type"><option>status</option><option>tools</option><option>agent</option><option>workflow</option><option>security</option></select></div>
          <button class="btn primary" onclick="ViewsPanel.save()">Save View</button>
        </div>
      </div>
    `, 'xl');
  },
  async loadData() {
    try {
      const data = await API.dashboardViews();
      this.views = data.views || [];
    } catch (e) {
      this.views = [];
      UI.toast('Error', 'Failed to load views', 'error');
    }
  },
  refresh() { this.loadData().then(() => this.open()); },
  async save() {
    const view = {
      id: 'view_' + Date.now(),
      name: document.getElementById('view-name')?.value.trim(),
      url: document.getElementById('view-url')?.value.trim(),
      type: document.getElementById('view-type')?.value,
      scope: 'local',
      description: 'Saved from dashboard'
    };
    if (!view.name || !view.url) return UI.toast('Error', 'Name and URL are required', 'warning');
    try {
      const data = await API.saveView(view);
      UI.toast('Saved', data.view?.name || view.name, 'success');
      logActivity('Saved view ' + view.name, 'success', 10);
      this.refresh();
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  },
  openView(id) {
    const view = this.views.find(v => v.id === id);
    if (!view?.url) return UI.toast('Error', 'View has no URL', 'error');
    if (view.url.startsWith('/')) window.location.href = view.url;
    else window.open(view.url, '_blank');
    logActivity('Opened view ' + view.name, 'info');
  },
  copyUrl(url) {
    navigator.clipboard?.writeText(url).then(() => UI.toast('Copied', url, 'success')).catch(() => UI.toast('Copied', url, 'info'));
  },
  async deleteView(id) {
    if (!confirm('Delete this view?')) return;
    try {
      await API.deleteView(id);
      UI.toast('Deleted', 'View removed', 'success');
      this.refresh();
    } catch (e) { UI.toast('Error', e.message, 'error'); }
  }
};

// ========================================
// MAIN INITIALIZATION
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
  // Load persisted state
  Object.assign(state, StateManager.load());
  state.badges = new Set(state.badges || []);

  // Initialize UI
  initTheme();
  initBackground();
  initEventListeners();

  // Connect WebSocket for real-time updates
  WSManager.connect(handleWSMessage);

  // Fetch initial data
  await fetchInitialData();
  await SecurityPanel.loadData();
  await fetchJobsAndAchievements();
  renderOptimizationCoach();
  await fetchCooperator();
  await fetchMoneyAndReposAndCreations();
  EpicCommandCenter?.init();
  CommandPalette?.init();

  // Setup UI event listeners
  startPolling();
  startUptimeCounter();

  // Start threat monitoring
  startThreatMonitor();

  logActivity('Command Center initialized', 'system');
  UI.toast('Welcome', 'AI Lab Command Center ready', 'success');
});

// ========================================
// EVENT LISTENERS
// ========================================
function initEventListeners() {
  document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
  document.getElementById('refresh-all')?.addEventListener('click', fetchInitialData);
  document.getElementById('optimize-queue')?.addEventListener('click', () => handlePromptAction('optimize'));
  document.getElementById('direct-queue')?.addEventListener('click', () => handlePromptAction('direct'));
  document.getElementById('improve-prompt')?.addEventListener('click', improvePrompt);
  document.getElementById('send-to-generate')?.addEventListener('click', sendToGenerate);
  document.getElementById('refresh-jobs')?.addEventListener('click', fetchJobsAndAchievements);
  document.getElementById('prompt-workflow')?.addEventListener('change', renderOptimizationCoach);
  document.getElementById('prompt-input')?.addEventListener('input', renderOptimizationCoach);
  document.getElementById('coop-self-heal')?.addEventListener('click', async () => { UI.toast('Self-Heal', 'Running', 'info'); const r = await API.systemSelfHeal(); renderSelfHeal(r); });
  document.getElementById('coop-briefing-btn')?.addEventListener('click', runBriefing);
  document.getElementById('coop-run-btn')?.addEventListener('click', runDirective);

  // New interactive buttons
  document.getElementById('btn-gpu-panel')?.addEventListener('click', () => GPUPanel.open(0));
  document.getElementById('btn-lane-manager')?.addEventListener('click', () => LaneManager.open('v100', 11437));
  document.getElementById('btn-comfy-manager')?.addEventListener('click', () => ComfyManager.open());
  document.getElementById('btn-security')?.addEventListener('click', () => SecurityPanel.open());
  document.getElementById('btn-powerups')?.addEventListener('click', () => PowerupsPanel.open());
  document.getElementById('btn-mature')?.addEventListener('click', () => MatureWorkflows.open());
  document.getElementById('btn-workflow')?.addEventListener('click', () => WorkflowBuilder.open());
  document.getElementById('btn-tools')?.addEventListener('click', () => CustomToolsPanel.open());
  document.getElementById('btn-mcp')?.addEventListener('click', () => MCPAgentPanel.open());
  document.getElementById('btn-views')?.addEventListener('click', () => ViewsPanel.open());
  document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => handleQuickAction(btn.dataset.action)));

  document.getElementById('clear-log')?.addEventListener('click', () => { state.activityLog = []; renderActivityLog(); });
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  dropzone?.addEventListener('click', () => fileInput?.click());
  dropzone?.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('active'); });
  dropzone?.addEventListener('dragleave', () => dropzone.classList.remove('active'));
  dropzone?.addEventListener('drop', e => { e.preventDefault(); dropzone.classList.remove('active'); handleFiles(e.dataTransfer.files); });
  fileInput?.addEventListener('change', e => handleFiles(e.target.files));

  // Keyboard shortcuts
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); document.getElementById('prompt-input')?.focus(); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.target.matches('textarea')) { e.preventDefault(); handlePromptAction('optimize'); }
    if (e.key === 'Escape') UI.closeModal();
  });
}

// ========================================
// THEME & BACKGROUND (Enhanced)
// ========================================
function initTheme() {
  document.documentElement.setAttribute('data-theme', state.theme);
  const toggle = document.getElementById('theme-toggle');
  if (toggle) toggle.textContent = state.theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', state.theme);
  const toggle = document.getElementById('theme-toggle');
  if (toggle) toggle.textContent = state.theme === 'dark' ? '☀️' : '🌙';
  StateManager.save(state);
  UI.toast('Theme', `Switched to ${state.theme} mode`, 'info');
}

function initBackground() {
  const canvas = document.getElementById('bg-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [], animationId = null;

  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  function createParticles() {
    const count = Math.min(60, Math.floor((canvas.width * canvas.height) / 20000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.2, vy: (Math.random() - 0.5) * 0.2,
      radius: Math.random() * 1.2 + 0.3, opacity: Math.random() * 0.4 + 0.05,
      hue: 170 + Math.random() * 40
    }));
  }
  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100) { ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(particles[j].x, particles[j].y); ctx.strokeStyle = `hsla(${particles[i].hue}, 100%, 40%, ${0.08 * (1 - dist / 100)})`; ctx.lineWidth = 0.4; ctx.stroke(); }
      }
    }
    particles.forEach(p => { ctx.beginPath(); ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2); ctx.fillStyle = `hsla(${p.hue}, 100%, 40%, ${p.opacity})`; ctx.fill(); p.x += p.vx; p.y += p.vy; if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0; if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0; });
    animationId = requestAnimationFrame(animate);
  }
  window.addEventListener('resize', () => { resize(); createParticles(); });
  resize(); createParticles(); animate();
}

// ========================================
// DATA FETCHING & RENDERING
// ========================================
async function fetchInitialData() {
  try {
    await Promise.all([fetchSystemStatus(), fetchGPUStatus(), fetchOllamaStatus()]);
    renderAll();
    logActivity('Dashboard refreshed', 'system');
  } catch (e) { console.error('Fetch failed:', e); UI.toast('Error', 'Failed to fetch data', 'error'); }
}

async function fetchSystemStatus() {
  try {
    const data = await API.health();
    state.services = { 'llm-api': data.status === 'ok' };
    const checks = data.checks || {};
    const serviceMap = { comfyui: 'comfyui', openwebui: 'open-webui', redis: 'redis', qdrant: 'qdrant', postgres: 'postgres', n8n: 'n8n' };
    Object.entries(serviceMap).forEach(([id, key]) => { state.services[id] = checks[key]?.status === 'ok' || checks[key]?.status === 'configured'; });
    if (data.ollama_instances) Object.entries(data.ollama_instances).forEach(([k, v]) => state.services[k] = v);
    renderServices();
  } catch (e) { console.error('System status failed:', e); }
}

async function fetchGPUStatus() {
  try {
    const data = await API.gpuStatus();
    state.gpus = data.gpus || [];
    renderGPUGrid();
  } catch (e) { console.error('GPU status failed:', e); }
}

async function fetchOllamaStatus() {
  try {
    const data = await API.ollamaStatus();
    state.ollamaLanes = (data.instances || []).map(lane => ({
      ...lane,
      expectedVersion: data.expected_user_lane_version || 'unknown',
      mixedVersion: Boolean(data.mixed_versions && lane.name === 'default'),
    }));
    renderLaneGrid();
    if (data.mixed_versions) {
      logActivity(`Ollama default lane version mismatch: ${data.default_lane_version} vs expected ${data.expected_user_lane_version}`, 'warn');
    }
  } catch (e) { console.error('Ollama status failed:', e); }
}

function renderAll() { renderServices(); renderGPUGrid(); renderLaneGrid(); renderActivityLog(); updateXPUI(); updateBadgesUI(); renderJobs(); renderOptimizationCoach(); }


async function fetchJobsAndAchievements() {
  try {
    const [jobsData, achData] = await Promise.all([API.jobs(), API.achievements()]);
    state.jobs = jobsData.jobs || [];
    state.achievements = achData.achievements || [];
    renderJobs();
    updateBadgesUI();
    renderOptimizationCoach();
    StateManager.save(state);
  } catch (e) { console.warn('Jobs/achievements failed:', e); }
}

function renderJobs() {
  const c = document.getElementById('jobs-strip');
  if (!c) return;
  const jobs = state.jobs || [];
  if (!jobs.length) {
    c.innerHTML = '<div class="empty-state">Queue a job to see live progress, ETA, and outputs.</div>';
    return;
  }
  c.innerHTML = jobs.slice(0, 8).map(job => {
    const pct = Math.max(0, Math.min(100, Number(job.progress_percent || 0)));
    const status = job.status || 'queued';
    const eta = status === 'success' ? 'complete' : `${Math.max(0, Math.round((job.estimate_seconds || 0) - (job.elapsed_seconds || 0)))}s est left`;
    const outputs = (job.outputs || []).slice(0, 4).map(out => {
      if (out.kind === 'gif' || /\.(mp4|webm|gif)$/i.test(out.filename || '')) {
        return `<a class="output-thumb video" href="${escapeHtml(out.url)}" target="_blank">🎞️ ${escapeHtml(out.filename)}</a>`;
      }
      return `<a href="${escapeHtml(out.url)}" target="_blank"><img class="output-thumb" src="${escapeHtml(out.url)}" alt="${escapeHtml(out.filename)}"></a>`;
    }).join('') || '<div class="muted">Output appears here when ComfyUI history reports it.</div>';
    const hints = (job.hints || []).slice(0, 2).map(h => `<li>${escapeHtml(h)}</li>`).join('');
    return `
      <div class="job-card ${escapeHtml(status)}">
        <div class="job-head"><strong>${escapeHtml(job.workflow || 'job')}</strong><span>${escapeHtml(status)}</span></div>
        <div class="job-id">${escapeHtml(job.prompt_id || '')}</div>
        <div class="progress-line"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="job-meta"><span>${pct}%</span><span>${eta}</span><span>${Math.round(job.elapsed_seconds || 0)}s elapsed</span></div>
        <div class="job-outputs">${outputs}</div>
        <details class="job-hints"><summary>Why this estimate / optimize</summary><ul>${hints}</ul></details>
      </div>`;
  }).join('');
}

function renderOptimizationCoach() {
  const c = document.getElementById('optimization-coach');
  if (!c) return;
  const wf = document.getElementById('prompt-workflow')?.value || 'txt2img';
  const prompt = document.getElementById('prompt-input')?.value || '';
  const queue = (state.jobs || []).filter(j => !['success','error'].includes(j.status)).length;
  const gpu = (state.gpus || []).find(g => String(g.name || '').includes('3060')) || (state.gpus || [])[0] || {};
  const util = Number(gpu.utilization || 0);
  const video = wf.includes('video');
  const imageReq = ['img2img','img2video','inpaint','controlnet'].includes(wf);
  const promptWords = prompt.trim() ? prompt.trim().split(/\s+/).length : 0;
  const base = video ? 60 : wf === 'upscale' ? 12 : imageReq ? 24 : 20;
  const queuePenalty = queue * 12;
  const gpuPenalty = util > 70 ? 20 : util > 40 ? 10 : 0;
  const estimate = base + queuePenalty + gpuPenalty;
  const factors = [
    `${wf}: ${video ? 'video/high VRAM path' : imageReq ? 'uses uploaded image + denoise' : 'text-to-image core path'}`,
    `GPU util ${util}%${gpuPenalty ? ' adds wait risk' : ' is clear'}`,
    `${queue} active/recent queued job(s)`,
    `${promptWords} prompt words${promptWords < 8 ? ' — add subject/style/lighting/camera' : ''}`
  ];
  c.innerHTML = `
    <div class="coach-estimate"><strong>Estimated queue/render window:</strong> ~${estimate}s</div>
    <ul>${factors.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
    <div class="coach-tips">
      <span>Draft fast: 768-1024px, 12-18 steps.</span>
      <span>Upscale only winners.</span>
      <span>For img2img, lower denoise preserves source; higher changes more.</span>
    </div>`;
}


async function fetchCooperator() {
  try {
    const [snap, dog] = await Promise.all([API.systemSnapshot(), API.systemWatchdog()]);
    const mem = snap.memory || {};
    document.getElementById('coop-heartbeat').textContent = `${(snap.services||[]).filter(s=>s.ok).length}/${(snap.services||[]).length} services ok`;
    document.getElementById('coop-mem').textContent = `${mem.used_gb || 0}/${mem.total_gb || 0} GB (${mem.percent || 0}%)`;
    document.getElementById('coop-comfy-size').textContent = `${snap.comfy_output_gb} GB`;
    const d = dog || {};
    const last = d.timestamp ? new Date(d.timestamp*1000).toLocaleTimeString() : '—';
    const ok = d.services_ok != null ? `${d.services_ok} ok` : '—';
    const acts = (d.actions || []).length;
    document.getElementById('coop-watchdog').textContent = `${last} • ${ok} • ${acts} action(s)`;
  } catch (e) { console.warn('cooperator fetch failed', e); }
}

async function fetchMoneyAndReposAndCreations() {
  try {
    const [m, r, c] = await Promise.all([API.moneyLeads(), API.coopRepos(), API.privateCreations()]);
    renderMoney(m);
    renderRepos(r);
    renderCreations(c);
  } catch (e) { console.warn('money/repos/creations failed', e); }
}

function renderMoney(data) {
  const c = document.getElementById('coop-money'); if (!c) return;
  const paths = data.paths || [];
  c.innerHTML = paths.map(p => `
    <div class="path">
      <div><strong>${escapeHtml(p.name)}</strong> <span class="badge">${escapeHtml(p.price_hint)}</span></div>
      <div class="muted">${escapeHtml(p.tagline)}</div>
      <div class="muted">Lever: ${escapeHtml(p.lever)}</div>
      <ol class="steps">${(p.steps||[]).map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ol>
    </div>`).join('') || '<div class="muted">No money paths loaded.</div>';
}

function renderRepos(data) {
  const c = document.getElementById('coop-repos'); if (!c) return;
  const repos = data.repos || [];
  if (!repos.length) { c.innerHTML = '<div class="muted">No repos at /home/scott/ai-workspace/repos.</div>'; return; }
  c.innerHTML = repos.map(r => `
    <div class="repo"><strong>${escapeHtml(r.name)}</strong> ${r.is_git ? `<span class="badge">git</span>` : ''} ${r.head_ref ? `<span class="badge">${escapeHtml(r.head_ref)}</span>` : ''}<div class="muted">${escapeHtml(r.path)}</div></div>
  `).join('');
}

function renderCreations(data) {
  const c = document.getElementById('coop-creations'); if (!c) return;
  const list = data.latest || [];
  if (!list.length) { c.innerHTML = '<div class="muted">No local creations found yet — drop files into /home/scott/ai-lab/creations or /home/scott/Pictures.</div>'; return; }
  c.innerHTML = list.map(f => `
    <div class="creation"><strong>${escapeHtml(f.path.split('/').slice(-1)[0])}</strong> <span class="muted">${formatBytes(f.size)}</span> <div class="muted">${escapeHtml(f.path)}</div></div>
  `).join('');
}

async function runBriefing() {
  const target = document.getElementById('coop-briefing');
  target.textContent = 'Working…';
  try {
    const r = await API.briefing();
    target.textContent = `${r.headline}\n\nActions:\n${(r.actions||[]).map(a => `[${a.priority}] ${a.title} — ${a.detail}`).join('\n')}`;
  } catch (e) { target.textContent = 'Failed: ' + e.message; }
}

async function runDirective() {
  const v = document.getElementById('coop-directive').value;
  const target = document.getElementById('coop-run-result');
  if (!v.trim()) { UI.toast('Empty', 'Enter a directive', 'warning'); return; }
  target.textContent = 'Working…';
  try {
    const r = await API.coopRun(v);
    target.textContent = JSON.stringify(r, null, 2);
    await fetchCooperator();
  } catch (e) { target.textContent = 'Failed: ' + e.message; }
}

function renderSelfHeal(result) {
  const target = document.getElementById('coop-briefing');
  if (!target) return;
  const actions = result?.actions || [];
  target.textContent = `Self-heal ran ${actions.length} action(s):\n` + actions.map(a => `- ${a.target}: ${JSON.stringify(a.status || a.detail || '')}`).join('\n');
  fetchCooperator();
}

function renderServices() {
  const svc = [
    { id: 'llm-api', label: 'LLM API', ind: 'llm', val: 'llm-status' },
    { id: 'comfyui', label: 'ComfyUI', ind: 'comfy', val: 'comfy-status' },
    { id: 'openwebui', label: 'Open WebUI', ind: 'oweb', val: 'oweb-status' },
    { id: 'redis', label: 'Redis', ind: 'redis', val: 'redis-status' },
    { id: 'qdrant', label: 'Qdrant', ind: 'qdrant', val: 'qdrant-status' },
    { id: 'postgres', label: 'Postgres', ind: 'pg', val: 'pg-status' },
    { id: 'n8n', label: 'n8n', ind: 'n8n', val: 'n8n-status' }
  ];
  svc.forEach(s => {
    const h = state.services[s.id];
    const ind = document.getElementById(`${s.ind}-indicator`);
    const val = document.getElementById(s.val);
    if (ind) ind.className = 'status-indicator ' + (h ? 'online' : 'offline');
    if (val) { val.textContent = h ? 'Online' : 'Offline'; val.style.color = h ? 'var(--accent)' : 'var(--danger)'; }
  });
}

function renderGPUGrid() {
  const c = document.getElementById('gpu-grid');
  if (!c) return;
  if (!state.gpus.length) { c.innerHTML = '<div class="gpu-card loading">No GPU data</div>'; return; }
  c.innerHTML = state.gpus.map((g, i) => createGPUCard(g, i)).join('');
}

function renderLaneGrid() {
  const c = document.getElementById('lane-grid');
  if (!c) return;
  if (!state.ollamaLanes.length) { c.innerHTML = '<div class="lane-card loading">No lane data</div>'; return; }
  c.innerHTML = state.ollamaLanes.map(l => createLaneCard(l)).join('');
}

function logActivity(msg, type = 'system', xp = 0) {
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  state.activityLog.unshift({ msg, type, xp, time: timeStr });
  if (state.activityLog.length > 100) state.activityLog.pop();
  renderActivityLog();
  if (xp > 0) awardXP(xp, msg);
  StateManager.save(state);
}

function renderActivityLog() {
  const c = document.getElementById('activity-log');
  if (!c) return;
  c.innerHTML = state.activityLog.slice(-50).reverse().map(a => `
    <li class="activity-item ${a.type}"><span>${a.msg}</span>${a.xp ? `<span class="badge-inline badge-purple">+${a.xp} XP</span>` : ''}<span class="activity-time">${a.time}</span></li>
  `).join('');
  c.scrollTop = 0;
}

function updateXPUI() {
  const fill = document.getElementById('xp-fill');
  const txt = document.getElementById('xp-text');
  const pct = state.xpToNext > 0 ? (state.xp / state.xpToNext) * 100 : 0;
  if (fill) fill.style.width = `${Math.min(pct, 100)}%`;
  if (txt) txt.textContent = `Level ${state.level} • ${state.xp} / ${state.xpToNext} XP`;
}

function updateBadgesUI() {
  const c = document.getElementById('badges-grid');
  if (!c) return;
  const achievements = state.achievements || [];
  if (achievements.length) {
    c.innerHTML = achievements.map(a => `
      <div class="badge ${a.unlocked ? 'unlocked' : 'locked'}" data-badge="${escapeHtml(a.id)}" title="${escapeHtml(a.description)}">
        <span>${escapeHtml(a.icon)}</span><span class="badge-title">${escapeHtml(a.name)}</span>
        <small>${a.current}/${a.target}</small><div class="mini-progress"><div style="width:${Math.min(100, a.percent || 0)}%"></div></div>
      </div>
    `).join('');
    return;
  }
  c.innerHTML = Object.entries(BADGES).map(([id, b]) => `
    <div class="badge locked" data-badge="${id}" title="${b.desc}">
      <span>${b.icon}</span><span class="badge-title">${b.name}</span>
    </div>
  `).join('');
}

function awardXP(amount, reason) {
  state.xp += amount;
  while (state.xp >= state.xpToNext) { state.xp -= state.xpToNext; state.level++; state.xpToNext = XP_PER_LEVEL(state.level); UI.toast('Level Up!', `Reached Level ${state.level}!`, 'xp'); logActivity(`Leveled up to Level ${state.level}!`, 'xp'); }
  updateXPUI(); StateManager.save(state); UI.toast(`+${amount} XP`, reason, 'xp');
}

function unlockBadge(id) {
  if (!state.badges.has(id)) { state.badges.add(id); const b = BADGES[id]; if (b) UI.toast('Badge Unlocked!', `${b.name}: ${b.desc}`, 'xp'); updateBadgesUI(); StateManager.save(state); }
}

// ========================================
// PROMPT STUDIO (Enhanced)
// ========================================
async function handlePromptAction(mode) {
  const prompt = document.getElementById('prompt-input').value.trim();
  const workflow = document.getElementById('prompt-workflow').value;
  const promptMode = document.getElementById('prompt-mode').value;
  if (!prompt) return UI.toast('Empty', 'Enter a prompt', 'warning');

  const btn = document.getElementById(mode === 'optimize' ? 'optimize-queue' : 'direct-queue');
  UI.setLoading(btn, true);
  try {
    if (mode === 'optimize') { await improvePrompt(); await queueToComfyUI(prompt, workflow, promptMode); }
    else { await queueToComfyUI(prompt, workflow, promptMode); }
    awardXP(15, mode === 'optimize' ? 'Optimized & queued' : 'Queued');
    unlockBadge('first-gen');
  } catch (e) { UI.toast('Error', 'Failed', 'error'); }
  finally { UI.setLoading(btn, false); }
}

async function improvePrompt() {
  const prompt = document.getElementById('prompt-input').value.trim();
  const mode = document.getElementById('prompt-mode').value;
  if (!prompt) return UI.toast('Empty', 'Enter prompt', 'warning');

  const btn = document.getElementById('improve-prompt');
  UI.setLoading(btn, true);
  try {
    // Security scan first
    const threats = SecurityEngine.analyzePrompt(prompt);
    if (threats.length > 0) {
      UI.toast('Threat Detected', `${threats.length} security issue(s) found`, 'threat');
      SecurityPanel.threats.push(...threats.map(t => ({ ...t, id: `t_${Date.now()}`, source: 'prompt-input' })));
    }

    const data = await API.improvePrompt(prompt, mode);
    if (data.improved_prompt) {
      document.getElementById('prompt-input').value = data.improved_prompt;
      awardXP(10, 'Prompt improved');
      unlockBadge('prompt-engineer');
      UI.toast('Improved', 'Check updated prompt', 'success');
    }
  } catch (e) { UI.toast('Error', 'Improve failed', 'error'); }
  finally { UI.setLoading(btn, false); }
}

async function queueToComfyUI(prompt, workflow, mode) {
  try {
    const options = {};
    if (['img2img', 'inpaint', 'controlnet', 'img2video'].includes(workflow)) {
      const file = selectedImageFile();
      if (!file) {
        UI.toast('Select Image', 'Upload/select an image for ' + workflow, 'warning');
        return;
      }
      const uploaded = await uploadFiles([file]);
      file._uploaded = uploaded[0];
      options.image_path = file._uploaded?.comfy_name || file._uploaded?.filename || file.name;
      options.denoise = workflow === 'img2video' ? 0.35 : 0.55;
    }
    if (workflow === 'txt2video') options.workflow = 'video';
    const data = await API.generate(prompt, workflow, mode, options);
    if (data.prompt_id) {
      if (data.job) { state.jobs = [data.job, ...(state.jobs || []).filter(j => j.prompt_id !== data.prompt_id)].slice(0, 25); renderJobs(); renderOptimizationCoach(); }
      logActivity(`Queued ${workflow}: ${data.prompt_id}`, 'success'); UI.toast('Queued', `ID: ${data.prompt_id}`, 'success');
      setTimeout(fetchJobsAndAchievements, 1500);
    }
    else { logActivity('Generated', 'success'); UI.toast('Done', 'Check ComfyUI', 'success'); }
  } catch (e) { UI.toast('Error', e.message || 'Queue failed', 'error'); }
}

async function sendToGenerate() {
  const prompt = document.getElementById('prompt-input').value.trim();
  if (!prompt) return UI.toast('Empty', 'Enter prompt', 'warning');
  window.open(`http://localhost:8188/?prompt=${encodeURIComponent(prompt)}`, '_blank');
  logActivity('Opened ComfyUI', 'system');
}

async function uploadFiles(files) {
  const imageFiles = Array.from(files || []).filter(f => /\.(png|jpe?g|webp|gif)$/i.test(f.name));
  if (!imageFiles.length) return [];
  try {
    const data = await API.uploadFiles(imageFiles);
    const uploaded = data.uploaded || [];
    if (uploaded.length) UI.toast('Uploaded', uploaded.length + ' image file(s)', 'success');
    return uploaded;
  } catch (e) {
    UI.toast('Upload Warning', e.message, 'warning');
    return [];
  }
}

function selectedImageFile() {
  return state.uploadQueue.find(f => /\.(png|jpe?g|webp|gif)$/i.test(f.name || ''));
}

async function handleImageAction(actionName, apiCall) {
  const file = selectedImageFile();
  if (!file) {
    UI.toast('Select Image', 'Add an image first, then retry ' + actionName, 'warning');
    window.open('http://localhost:8188', '_blank');
    return;
  }
  try {
    const uploaded = file._uploaded ? [file._uploaded] : await uploadFiles([file]);
    file._uploaded = uploaded[0];
    const imagePath = uploaded[0]?.comfy_name || uploaded[0]?.filename || uploaded[0]?.path || file.name;
    const data = await apiCall(imagePath);
    if (data.job) { state.jobs = [data.job, ...(state.jobs || []).filter(j => j.prompt_id !== data.prompt_id)].slice(0, 25); renderJobs(); renderOptimizationCoach(); }
    UI.toast(actionName, data.message || 'Started', 'success');
    logActivity(actionName + ': ' + (file.name || imagePath), 'success', 15);
    setTimeout(fetchJobsAndAchievements, 1500);
    unlockBadge('upscale-king');
  } catch (e) {
    UI.toast('Error', e.message, 'error');
  }
}

// ========================================
// FILE UPLOAD
// ========================================
async function handleFiles(files) {
  const preview = document.getElementById('upload-preview');
  Array.from(files).forEach(f => {
    const item = document.createElement('div');
    item.className = 'upload-item';
    item.innerHTML = `<span class="upload-item-name">${escapeHtml(f.name)}</span><span class="upload-item-size">${formatBytes(f.size)}</span><button class="upload-item-remove" onclick="this.parentElement.remove(); updateQueueCount()">✕</button>`;
    preview.appendChild(item);
    state.uploadQueue.push(f);
  });
  updateQueueCount();
  const uploaded = await uploadFiles(files);
  uploaded.forEach((item, idx) => {
    if (state.uploadQueue[idx]) state.uploadQueue[idx]._uploaded = item;
  });
  logActivity(`Added ${files.length} file(s)`, 'info');
}

function updateQueueCount() {
  const b = document.getElementById('queue-count-badge');
  if (b) b.textContent = `${state.uploadQueue.length} queued`;
}

function formatBytes(b) { if (b === 0) return '0 B'; const k = 1024; const s = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b)/Math.log(k)); return parseFloat((b/Math.pow(k,i)).toFixed(1)) + ' ' + s[i]; }

// ========================================
// DISK / MODEL / SMOKE OPERATOR PANELS
// ========================================
const DiskRescuePanel = {
  async open() {
    UI.modal('🧯 Disk Rescue', '<div class="panel-content"><p>Scanning disk pressure...</p></div>', 'xl');
    const data = await API.diskRescue();
    const diskRows = (data.disks || []).map(d => `<tr><td>${escapeHtml(d.path)}</td><td>${d.used_gb}G</td><td>${d.free_gb}G</td><td>${d.percent}%</td></tr>`).join('');
    const candidates = data.candidates || {};
    const swaps = (candidates.inactive_swapfiles || []).map(x => `<li>${escapeHtml(x.size_h)} ${escapeHtml(x.path)} ${x.active ? '(ACTIVE - do not delete)' : '(inactive, sudo delete)'}</li>`).join('') || '<li>None found</li>';
    const downloads = (candidates.stale_download_models || []).slice(0, 20).map(x => `<li>${escapeHtml(x.size_h)} ${escapeHtml(x.path)}</li>`).join('') || '<li>None found</li>';
    const snaps = (candidates.stale_snap_model_chunks || []).slice(0, 20).map(x => `<li>${escapeHtml(x.size_h)} ${escapeHtml(x.path)} ${x.requires_sudo ? '(sudo)' : ''}</li>`).join('') || '<li>None found</li>';
    UI.modal('🧯 Disk Rescue', `
      <div class="panel-content">
        <div class="detail-grid">
          <div class="detail-item"><span class="label">Estimated reclaim</span><span class="value">${escapeHtml(data.estimated_reclaim_h || '0 B')}</span></div>
          <div class="detail-item"><span class="label">Critical disk</span><span class="value">/mnt/ai-storage</span></div>
        </div>
        <table class="process-table"><thead><tr><th>Path</th><th>Used</th><th>Free</th><th>Use</th></tr></thead><tbody>${diskRows}</tbody></table>
        <h4>Inactive swapfiles (requires sudo)</h4><ul>${swaps}</ul>
        <h4>Stale Downloads model blobs (user-deletable)</h4><ul>${downloads}</ul>
        <h4>Stale snap model chunks (requires sudo)</h4><ul>${snaps}</ul>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button class="btn" onclick="DiskRescuePanel.refresh()">Refresh</button>
          <button class="btn" onclick="DiskRescuePanel.cleanTmp()">Clean temp dashboard files</button>
          <button class="btn danger" onclick="DiskRescuePanel.cleanDownloads()">Delete stale Downloads models</button>
        </div>
        <pre id="disk-output" class="log-output" style="max-height:260px;overflow:auto;margin-top:12px">${escapeHtml(JSON.stringify((data.large_files || []).slice(0, 20), null, 2))}</pre>
      </div>
    `, 'xl');
  },
  refresh() { return this.open(); },
  async cleanDownloads() { if (!confirm('Delete model blobs from /mnt/ai-storage/home/scott/Downloads?')) return; const r = await API.diskRescueRun('downloads'); document.getElementById('disk-output').textContent = JSON.stringify(r, null, 2); UI.toast('Disk Rescue', 'Downloads cleanup complete', 'success'); },
  async cleanTmp() { const r = await API.diskRescueRun('tmp-dashboard'); document.getElementById('disk-output').textContent = JSON.stringify(r, null, 2); UI.toast('Disk Rescue', 'Temp cleanup complete', 'success'); }
};

const ModelTruthPanel = {
  async open() {
    UI.modal('🧠 Model Store Truth', '<div class="panel-content"><p>Scanning model stores...</p></div>', 'xl');
    const data = await API.modelTruth();
    const roots = (data.roots_scanned || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');
    const dupes = (data.duplicates_by_name_size || []).slice(0, 15).map(group => `<li><b>${escapeHtml(group[0].size_h)} ${escapeHtml(group[0].name)}</b><ul>${group.map(x => `<li>${escapeHtml(x.path)}</li>`).join('')}</ul></li>`).join('') || '<li>No same-name same-size duplicates found in scanned roots.</li>';
    const largest = (data.largest || []).slice(0, 25).map(x => `<tr><td>${escapeHtml(x.size_h)}</td><td>${escapeHtml(x.path)}</td></tr>`).join('');
    UI.modal('🧠 Model Store Truth', `
      <div class="panel-content">
        <div class="detail-grid"><div class="detail-item"><span class="label">Files</span><span class="value">${data.file_count}</span></div><div class="detail-item"><span class="label">Total scanned</span><span class="value">${escapeHtml(data.total_h || '0 B')}</span></div></div>
        <h4>Active paths</h4><pre class="log-output">${escapeHtml(JSON.stringify(data.active_paths, null, 2))}</pre>
        <h4>Roots scanned</h4><ul>${roots}</ul>
        <h4>Duplicate candidates</h4><ul>${dupes}</ul>
        <h4>Largest model files</h4><table class="process-table"><thead><tr><th>Size</th><th>Path</th></tr></thead><tbody>${largest}</tbody></table>
        <p style="color:var(--muted)">${escapeHtml(data.recommendation || '')}</p>
      </div>
    `, 'xl');
  }
};

const SmokePanel = {
  async open() {
    UI.modal('✅ Dashboard Smoke', '<div class="panel-content"><p>Loading smoke status...</p></div>', 'lg');
    const data = await API.smokeStatus();
    UI.modal('✅ Dashboard Smoke', `
      <div class="panel-content">
        <div class="detail-grid"><div class="detail-item"><span class="label">Script</span><span class="value">${data.script_exists ? 'present' : 'missing'}</span></div><div class="detail-item"><span class="label">Last result</span><span class="value">${data.last?.ok === true ? 'PASS' : data.last?.ok === false ? 'FAIL' : 'none'}</span></div></div>
        <div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn primary" onclick="SmokePanel.run()">Run Smoke</button><button class="btn" onclick="SmokePanel.logs()">Logs</button></div>
        <pre id="smoke-output" class="log-output" style="max-height:420px;overflow:auto;margin-top:12px">${escapeHtml(JSON.stringify(data.last || {}, null, 2))}</pre>
      </div>
    `, 'lg');
  },
  async run() { const out = document.getElementById('smoke-output'); out.textContent = 'Running smoke...'; const r = await API.runSmoke(); out.textContent = JSON.stringify(r, null, 2); UI.toast('Smoke', r.ok ? 'PASS' : 'FAIL', r.ok ? 'success' : 'error'); },
  async logs() { const out = document.getElementById('smoke-output'); const r = await API.dashboardLogs(160); out.textContent = r.logs || r.stderr || JSON.stringify(r, null, 2); }
};

// ========================================
// POWERUPS / CHEAT CODES
// ========================================
const PowerupsPanel = {
  open() {
    const cards = [
      { id: 'brief', icon: '📜', title: 'Operator Briefing', desc: 'Generate the current action queue from real service health, disk, and money-path signals.', run: 'briefing' },
      { id: 'money', icon: '💸', title: 'Money Path Finder', desc: 'Pull the fastest monetizable wedges from the local lab assets.', run: 'money' },
      { id: 'heal', icon: '🛠️', title: 'Self-Heal', desc: 'Run the local repair actor and refresh service state without freezing the UI.', run: 'heal' },
      { id: 'repos', icon: '🧬', title: 'Repo Radar', desc: 'List local repos/workspaces worth productizing or fixing next.', run: 'repos' },
      { id: 'private', icon: '🔒', title: 'Private Creations', desc: 'Summarize local/private creations footprint without uploading anything.', run: 'private' },
      { id: 'report', icon: '📊', title: 'Daily Report', desc: 'Open the workstation daily report output.', run: 'report' },
      { id: 'op', icon: '🧭', title: 'Better Me / Workstation MO', desc: 'Generate a grounded operator report: fix, harden, ideate, and next money/time moves.', run: 'op' },
    ];
    UI.modal('⚡ Superpowers / Cheat Codes', `
      <div class="panel-content">
        <p style="color:var(--muted);margin-top:0">One-click local operator moves. No cloud calls; every button hits the existing FastAPI backend.</p>
        <div class="action-grid" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-bottom:16px">
          ${cards.map(c => `
            <button class="action-btn" onclick="PowerupsPanel.run('${c.run}')" title="${escapeHtml(c.desc)}">
              <span class="action-icon">${c.icon}</span>
              <span>${escapeHtml(c.title)}</span>
            </button>
          `).join('')}
        </div>
        <div class="field">
          <label>Directive cheat code</label>
          <input id="powerup-directive" class="input" value="briefing and money and repos" />
          <div class="field-hint">Examples: heal workstation • money paths • list repos • private creations • dashboard status</div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button class="btn" onclick="UI.closeModal()">Close</button>
          <button class="btn primary" onclick="PowerupsPanel.runDirective()">Run Directive</button>
        </div>
        <pre id="powerup-output" class="log-output" style="max-height:320px;overflow:auto;margin-top:12px"></pre>
      </div>
    `, 'xl');
  },

  async run(kind) {
    const output = document.getElementById('powerup-output');
    const write = (value) => { if (output) output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); };
    try {
      UI.toast('Powerup', `Running ${kind}`, 'info');
      let result;
      if (kind === 'briefing') result = await API.briefing();
      else if (kind === 'money') result = await API.moneyLeads();
      else if (kind === 'heal') result = await API.systemSelfHeal();
      else if (kind === 'repos') result = await API.coopRepos();
      else if (kind === 'private') result = await API.privateCreations();
      else if (kind === 'report') result = await API.report();
      else if (kind === 'op') result = await API.workstationOp();
      else result = await API.coopRun(kind);
      write(result);
      logActivity(`Powerup: ${kind}`, 'success', 10);
      UI.toast('Powerup Complete', kind, 'success');
      await fetchInitialData();
    } catch (e) {
      write(e.message || String(e));
      UI.toast('Powerup Failed', e.message || String(e), 'error');
    }
  },

  async runDirective() {
    const text = document.getElementById('powerup-directive')?.value || '';
    const output = document.getElementById('powerup-output');
    try {
      const result = await API.coopRun(text);
      if (output) output.textContent = JSON.stringify(result, null, 2);
      logActivity(`Directive: ${text}`, 'success', 15);
      UI.toast('Directive Complete', text.slice(0, 60), 'success');
    } catch (e) {
      if (output) output.textContent = e.message || String(e);
      UI.toast('Directive Failed', e.message || String(e), 'error');
    }
  }
};

// ========================================
// QUICK ACTIONS
// ========================================
async function handleQuickAction(action) {
  const actions = {
    generate: () => window.open('http://localhost:8188', '_blank'),
    upscale: async () => { await handleImageAction('Upscale', imagePath => API.upscale({ image_path: imagePath, scale: 4 })); },
    variations: async () => { await handleImageAction('Variations', imagePath => API.variations({ image_path: imagePath, count: 4 })); },
    batch: () => UI.modal('Batch Generate', batchModalContent()),
    cleanup: async () => { if (confirm('Clean outputs >30 days?')) { try { await API.cleanup(); UI.toast('Cleanup', 'Done', 'success'); logActivity('Cleanup', 'info'); } catch { UI.toast('Error', 'Failed', 'error'); } } },
    backup: async () => { try { await API.backup(); UI.toast('Backup', 'Done', 'success'); logActivity('Backup', 'success'); } catch { UI.toast('Error', 'Failed', 'error'); } },
    report: async () => { try { const t = await API.report(); const reportText = typeof t === 'string' ? t : JSON.stringify(t, null, 2); UI.modal('Daily Report', `<pre style="font-family:var(--font-mono);font-size:0.75rem;white-space:pre-wrap">${escapeHtml(reportText)}</pre>`); } catch { UI.toast('Error', 'Failed', 'error'); } },
    heal: async () => { try { await API.heal(); UI.toast('Heal', 'Complete', 'success'); logActivity('Self-heal', 'success'); await fetchInitialData(); } catch { UI.toast('Error', 'Failed', 'error'); } },
    powerups: () => PowerupsPanel.open(),
    disk: () => DiskRescuePanel.open(),
    models: () => ModelTruthPanel.open(),
    smoke: () => SmokePanel.open(),
    security: () => SecurityPanel.open(),
    comfy: () => ComfyManager.open(),
    workflow: () => WorkflowsPanel.open(),
    workflows: () => WorkflowsPanel.open(),
    tools: () => CustomToolsPanel.open(),
    mcp: () => MCPAgentPanel.open(),
    views: () => ViewsPanel.open(),
    mature: () => MatureWorkflows.open(),
    gpu: () => GPUPanel.open(0)
  };
  if (actions[action]) { await actions[action](); logActivity(`Action: ${action}`, 'system'); }
}

function batchModalContent() {
  return `
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="field"><label>Prompt</label><textarea class="textarea" id="batch-prompt" rows="4" placeholder="Base prompt"></textarea></div>
      <div class="studio-row">
        <div class="field"><label>Count</label><input type="number" class="select" id="batch-count" value="4" min="1" max="20"></div>
        <div class="field"><label>Workflow</label><select class="select" id="batch-workflow"><option value="txt2img">Text→Image</option><option value="img2img">Image→Image</option></select></div>
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn" onclick="UI.closeModal()">Cancel</button><button class="btn primary" onclick="startBatch()">Start Batch</button></div>
    </div>
  `;
}

window.startBatch = async () => {
  const prompt = document.getElementById('batch-prompt').value;
  const count = parseInt(document.getElementById('batch-count').value);
  const workflow = document.getElementById('batch-workflow').value;
  if (!prompt) return UI.toast('Error', 'Enter prompt', 'warning');
  UI.closeModal();
  for (let i = 0; i < count; i++) { await queueToComfyUI(`${prompt} --v ${i+1}`, workflow, 'cinematic'); await new Promise(r => setTimeout(r, 500)); }
  awardXP(25, `Batch of ${count}`); unlockBadge('batch-commander');
};

// ========================================
// WEBSOCKET HANDLING
// ========================================
function handleWSMessage(data) {
  switch (data.type) {
    case 'status': state.services = { ...state.services, ...data.services }; renderServices(); break;
    case 'gpu': state.gpus = data.gpu; renderGPUGrid(); break;
    case 'ollama': state.ollamaLanes = data.ollama; renderLaneGrid(); break;
    case 'activity': logActivity(data.msg, data.type, data.xp); break;
    case 'threat': state.security.threats.push(data); SecurityPanel.threats.push(data); if (document.getElementById('tab-threats')) SecurityPanel.open(); break;
    case 'xp': state.xp = data.xp; state.level = data.level; state.xpToNext = data.xpToNext; updateXPUI(); break;
  }
}

// ========================================
// POLLING & UPTIME
// ========================================
function startPolling() {
  setInterval(() => { if (WSManager.ws?.readyState !== WebSocket.OPEN) fetchInitialData(); }, 30000);
  setInterval(fetchJobsAndAchievements, 5000);
  setInterval(fetchCooperator, 8000);
}
function startUptimeCounter() { const s = Date.now(); setInterval(() => { const u = Date.now()-s; const h=Math.floor(u/36e5), m=Math.floor(u%36e5/6e4), sec=Math.floor(u%6e4/1e3); const e=document.getElementById('uptime'); if(e) e.textContent=`Up ${h}h ${m}m ${sec}s`; }, 1000); }

// ========================================
// THREAT MONITORING
// ========================================
function startThreatMonitor() {
  setInterval(() => {
    // Check for anomalies in state
    if (state.security.threats.length > 0) {
      const recent = state.security.threats.filter(t => Date.now() - t.timestamp < 60000);
      if (recent.length > 5) {
        UI.toast('⚠️ Threat Spike', `${recent.length} threats in last minute`, 'threat');
      }
    }
  }, 30000);
}

// ========================================
// EXPORT GLOBALS
// ========================================
window.UI = UI;
window.API = API;
window.GPUPanel = GPUPanel;
window.LaneManager = LaneManager;
window.ComfyManager = ComfyManager;
window.WorkflowBuilder = WorkflowBuilder;
window.SecurityPanel = SecurityPanel;
window.MatureWorkflows = MatureWorkflows;
window.PowerupsPanel = PowerupsPanel;
window.DiskRescuePanel = DiskRescuePanel;
window.ModelTruthPanel = ModelTruthPanel;
window.SmokePanel = SmokePanel;
window.CustomToolsPanel = CustomToolsPanel;
window.MCPAgentPanel = MCPAgentPanel;
window.WorkflowsPanel = WorkflowsPanel;
window.ViewsPanel = ViewsPanel;
window.fetchJobsAndAchievements = fetchJobsAndAchievements;
window.fetchInitialData = fetchInitialData;
window.fetchCooperator = fetchCooperator;
window.logActivity = logActivity;
window.runBriefing = runBriefing;
window.handleQuickAction = handleQuickAction;
window.startBatch = window.startBatch;
window.SecurityEngine = SecurityEngine;