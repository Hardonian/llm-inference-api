// Epic / Breaker Powerups Module for AI Lab Command Center
// R8: WebSocket push consumer
// R9: UX polish — arrow keys, fuzzy search, recent commands, mobile, delta arrows

if (typeof escapeHtml !== 'function') {
  window.escapeHtml = function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  };
}

// ======================== FUZZY SEARCH ========================
function fuzzyMatch(query, text) {
  query = query.toLowerCase();
  text = text.toLowerCase();
  if (!query) return { match: true, score: 0 };
  if (text.includes(query)) return { match: true, score: 100 - text.indexOf(query) };
  let qi = 0, score = 0, lastMatch = -1;
  for (let ti = 0; ti < text.length && qi < query.length; ti++) {
    if (text[ti] === query[qi]) {
      score += (ti === lastMatch + 1) ? 10 : 1; // consecutive bonus
      lastMatch = ti;
      qi++;
    }
  }
  return { match: qi === query.length, score };
}

// ======================== EPIC HUD (R8: WebSocket) ========================
const EpicCommandCenter = {
  output: null,
  ws: null,
  wsReconnectDelay: 1000,
  hudData: { revenue_readiness: 0, services_ok: 0, predictions: [] },
  
  init() {
    this.output = document.getElementById('epic-output');
    document.getElementById('epic-revenue-btn')?.addEventListener('click', () => this.run('revenue'));
    document.getElementById('epic-predict-btn')?.addEventListener('click', () => this.run('predictions'));
    document.getElementById('epic-improve-btn')?.addEventListener('click', () => this.run('improvements'));
    document.getElementById('epic-packs-btn')?.addEventListener('click', () => this.run('packs'));
    document.getElementById('epic-command-btn')?.addEventListener('click', () => CommandPalette.open());
    document.getElementById('epic-trends-btn')?.addEventListener('click', () => this.run('trends'));
    document.getElementById('epic-insights-btn')?.addEventListener('click', () => this.run('insights'));
    this.refreshHUD();
    this.connectWS();
    // Fallback: poll every 30s if WS not connected
    setInterval(() => { if (!this.ws || this.ws.readyState !== 1) this.refreshHUD(); }, 30000);
  },
  
  // R8: WebSocket consumer with auth + auto-reconnect + backoff
  connectWS() {
    try {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const token = window.__DASHBOARD_TOKEN__ || document.querySelector('meta[name="dashboard-token"]')?.content;
      const url = new URL(`${proto}//${location.host}/ws/epic`);
      if (token) url.searchParams.set('token', token);
      this.ws = new WebSocket(url.toString());
      this.ws.onopen = () => {
        this.wsReconnectDelay = 1000;
        console.log('[Epic WS] connected');
        try {
          this.ws.send(JSON.stringify({
            type: 'hello',
            subscribe: ['revenue_change', 'disk_alert', 'service_down', 'prediction_update', 'agent_complete'],
            last_seq: 0,
          }));
        } catch (e) {
          console.warn('[Epic WS] hello failed', e);
        }
      };
      this.ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === 'state_sync' && data.payload) {
            this.hudData = {
              ...this.hudData,
              revenue: data.payload.revenue,
              predictions: data.payload.predictions?.predictions || data.payload.predictions || [],
              improvements: data.payload.improvements,
              workflow_packs: data.payload.workflows,
              health: data.payload.system,
              services_ok: Array.isArray(data.payload.system?.services)
                ? data.payload.system.services.filter(s => s.ok).length
                : (data.payload.system?.services_ok ?? this.hudData.services_ok),
            };
            this.updateHUDFromData();
            return;
          }
          if (data.type === 'tick') {
            this.hudData = { ...this.hudData, ...data };
            this.updateHUDFromData();
            return;
          }
          if (data.type === 'heartbeat' || data.type === 'pong') return;
          if (data.payload) {
            this.hudData = { ...this.hudData, last_event: data };
            this.updateHUDFromData();
          }
        } catch (e) { /* ignore parse errors */ }
      };
      this.ws.onclose = () => {
        const delay = Math.min(this.wsReconnectDelay, 30000);
        console.log(`[Epic WS] closed, reconnect in ${delay}ms`);
        setTimeout(() => this.connectWS(), delay);
        this.wsReconnectDelay = Math.min(this.wsReconnectDelay * 2, 30000);
      };
      this.ws.onerror = () => { /* onclose will fire */ };
    } catch (e) {
      console.warn('[Epic WS] init failed', e);
    }
  },
  
  write(value) {
    if (!this.output) return;
    this.output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  },
  
  async refreshHUD() {
    try {
      const r = await fetch('/api/epic/dashboard', { headers: CommandPalette.authHeaders() });
      if (r.ok) {
        const data = await r.json();
        this.hudData = { ...this.hudData, ...data };
        this.updateHUDFromData();
      }
    } catch (e) { console.warn('Epic HUD refresh failed', e); }
  },
  
  updateHUDFromData() {
    const d = this.hudData;
    this._setText('revenue-score', `${d.revenue_readiness ?? d.revenue?.overall_readiness ?? 0}%`);
    this._setText('revenue-next', d.next_action || d.revenue?.next_action || 'Scan revenue');
    const preds = d.predictions;
    if (Array.isArray(preds) && preds.length > 0) {
      const p = preds[0];
      this._setText('prediction-risk', (p?.risk || '—').toUpperCase());
      this._setText('prediction-days', p?.days_to_full ? `${p.days_to_full}d to full` : 'trend N/A');
      // Color-code risk
      const riskEl = document.getElementById('prediction-risk');
      if (riskEl) {
        riskEl.className = 'epic-value';
        if (p?.risk === 'critical') riskEl.classList.add('risk-critical');
        else if (p?.risk === 'high') riskEl.classList.add('risk-high');
        else if (p?.risk === 'med') riskEl.classList.add('risk-medium');
      }
    }
    const imp_count = d.improvements?.count ?? 0;
    this._setText('improve-count', imp_count);
    this._setText('improve-top', d.improvements?.top?.title || '—');
    const pack_count = d.workflow_packs?.ready_count ?? 0;
    this._setText('packs-count', pack_count);
    this._setText('packs-top', d.workflow_packs?.top?.workflow || '—');
    // Services health bar
    const svc_ok = d.health?.services_ok ?? d.services_ok ?? 0;
    const svc_total = d.health?.services_total ?? 8;
    this._setText('services-status', `${svc_ok}/${svc_total}`);
  },
  
  _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  },
  
  async run(kind) {
    if (!this.output) return;
    if (typeof UI !== 'undefined') UI.toast('Epic', `Running ${kind}`, 'info');
    try {
      let result;
      const hdrs = CommandPalette.authHeaders();
      if (kind === 'revenue') result = await (await fetch('/api/revenue/status', { headers: hdrs })).json();
      else if (kind === 'predictions') result = await (await fetch('/api/system/predictions', { headers: hdrs })).json();
      else if (kind === 'improvements') result = await (await fetch('/api/agent/improvements', { headers: hdrs })).json();
      else if (kind === 'packs') result = await (await fetch('/api/workflows/productize', { headers: hdrs })).json();
      else if (kind === 'trends') result = await (await fetch('/api/trends', { headers: hdrs })).json();
      else if (kind === 'insights') result = await (await fetch('/api/insights', { headers: hdrs })).json();
      else result = await (await fetch('/api/agent/command', { method: 'POST', headers: { ...hdrs, 'Content-Type': 'application/json' }, body: JSON.stringify({ directive: kind }) })).json();
      this.write(result);
      if (typeof logActivity === 'function') logActivity(`Epic ${kind}`, 'success', 10);
      if (typeof UI !== 'undefined') UI.toast('Epic Complete', kind, 'success');
    } catch (e) {
      this.write(e.message || String(e));
      if (typeof UI !== 'undefined') UI.toast('Epic Failed', e.message || String(e), 'error');
    }
  }
};

// ======================== COMMAND PALETTE (R9: UX Polish) ========================
const CommandPalette = {
  el: null,
  input: null,
  results: null,
  selectedIndex: 0,
  filteredCommands: [],
  RECENT_KEY: 'epic_recent_commands',
  
  commands: [
    { id: 'heal', title: 'Heal Workstation', shortcut: 'heal', icon: '🔧', run: () => EpicCommandCenter.run('heal') },
    { id: 'money', title: 'Show Money Paths / Revenue', shortcut: 'money', icon: '💰', run: () => EpicCommandCenter.run('revenue') },
    { id: 'disk', title: 'Disk Rescue Report', shortcut: 'disk rescue', icon: '💾', run: () => typeof DiskRescuePanel !== 'undefined' ? DiskRescuePanel.open() : EpicCommandCenter.run('disk') },
    { id: 'models', title: 'Model Store Truth', shortcut: 'models', icon: '🧠', run: () => typeof ModelTruthPanel !== 'undefined' ? ModelTruthPanel.open() : EpicCommandCenter.run('models') },
    { id: 'improve', title: 'Self-Improvement Suggestions', shortcut: 'improve', icon: '📈', run: () => EpicCommandCenter.run('improvements') },
    { id: 'predict', title: 'Predictive Monitoring', shortcut: 'predict', icon: '🔮', run: () => EpicCommandCenter.run('predictions') },
    { id: 'packs', title: 'Workflow Product Packs', shortcut: 'packs', icon: '📦', run: () => EpicCommandCenter.run('packs') },
    { id: 'trends', title: 'Trends (7d/30d/90d)', shortcut: 'trends', icon: '📊', run: () => EpicCommandCenter.run('trends') },
    { id: 'insights', title: 'Strategic Insights', shortcut: 'insights', icon: '🎯', run: () => EpicCommandCenter.run('insights') },
    { id: 'brief', title: 'Operator Briefing', shortcut: 'brief', icon: '📋', run: () => typeof runBriefing === 'function' && runBriefing() },
    { id: 'repos', title: 'Repo Radar', shortcut: 'repos', icon: '🔍', run: () => fetch('/api/cooperator/repos', { headers: CommandPalette.authHeaders() }).then(r => r.json()).then(r => { if (typeof UI !== 'undefined') UI.modal('Repo Radar', `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`); }) },
    { id: 'private', title: 'Private Creations', shortcut: 'private', icon: '🎨', run: () => fetch('/api/private-creations', { headers: CommandPalette.authHeaders() }).then(r => r.json()).then(r => { if (typeof UI !== 'undefined') UI.modal('Private Creations', `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`); }) },
    { id: 'powerups', title: 'Open Powerups Panel', shortcut: 'powerups', icon: '⚡', run: () => typeof PowerupsPanel !== 'undefined' && PowerupsPanel.open() },
    { id: 'smoke', title: 'Run Dashboard Smoke Test', shortcut: 'smoke', icon: '🧪', run: () => fetch('/api/dashboard/smoke', { method: 'POST', headers: CommandPalette.authHeaders() }).then(r => r.json()).then(r => { if (typeof UI !== 'undefined') UI.toast('Smoke', `${r.ok ? 'OK' : 'FAIL'}`, r.ok ? 'success' : 'error'); }) },
    { id: 'export-rev', title: 'Export Revenue Report (Markdown)', shortcut: 'export revenue', icon: '📄', run: () => window.open('/api/revenue/export', '_blank') },
    { id: 'export-rev-json', title: 'Export Revenue Report (JSON)', shortcut: 'export json revenue', icon: '📋', run: () => window.open('/api/revenue/export.json', '_blank') },
    { id: 'export-pred', title: 'Export Predictions (Markdown)', shortcut: 'export predictions', icon: '📄', run: () => window.open('/api/predictions/export', '_blank') },
    { id: 'export-disk', title: 'Export Disk Rescue (Markdown)', shortcut: 'export disk', icon: '📄', run: () => window.open('/api/disk/rescue/export', '_blank') },
    { id: 'refresh', title: 'Refresh Dashboard', shortcut: 'refresh', icon: '🔄', run: () => typeof fetchInitialData === 'function' && fetchInitialData() },
    { id: 'theme', title: 'Toggle Theme', shortcut: 'theme', icon: '🌓', run: () => document.getElementById('theme-toggle')?.click() },
    { id: 'p50', title: 'Show P50/P95 Latency', shortcut: 'latency', icon: '⏱️', run: () => fetch('/api/p50', { headers: CommandPalette.authHeaders() }).then(r => r.json()).then(r => { if (typeof UI !== 'undefined') UI.modal('Endpoint Latency', `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`); }) },
  ],
  
  authHeaders() {
    const token = window.__DASHBOARD_TOKEN__ || document.querySelector('meta[name="dashboard-token"]')?.content;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  },
  
  init() {
    this.el = document.getElementById('command-palette');
    this.input = document.getElementById('command-palette-input');
    this.results = document.getElementById('command-palette-results');
    document.getElementById('command-palette-close')?.addEventListener('click', () => this.close());
    this.input?.addEventListener('input', () => { this.selectedIndex = 0; this.render(); });
    this.input?.addEventListener('keydown', (e) => this.handleKeydown(e));
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); this.open(); }
      if (e.key === 'Escape' && this.el && !this.el.classList.contains('hidden')) { this.close(); }
    });
  },
  
  handleKeydown(e) {
    if (e.key === 'Escape') { this.close(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, this.filteredCommands.length - 1);
      this.highlightSelected();
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
      this.highlightSelected();
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const q = this.input.value.trim();
      if (this.filteredCommands[this.selectedIndex]) {
        const cmd = this.filteredCommands[this.selectedIndex];
        this.close();
        this.saveRecent(cmd.id);
        cmd.run();
      } else if (q) {
        this.runNatural(q);
      }
      return;
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      // Tab cycles through filtered results
      this.selectedIndex = (this.selectedIndex + 1) % Math.max(this.filteredCommands.length, 1);
      this.highlightSelected();
    }
  },
  
  open() {
    if (!this.el) return;
    this.el.classList.remove('hidden');
    this.input.value = '';
    this.input.focus();
    this.selectedIndex = 0;
    this.render();
  },
  
  close() {
    if (!this.el) return;
    this.el.classList.add('hidden');
  },
  
  render() {
    const q = (this.input.value || '').toLowerCase();
    let matches;
    if (q) {
      matches = this.commands
        .map(c => ({ ...c, ...fuzzyMatch(q, c.title + ' ' + c.shortcut) }))
        .filter(c => c.match)
        .sort((a, b) => b.score - a.score);
    } else {
      // Show recent commands first, then all
      const recent = this.getRecent();
      const recentCmds = recent.map(id => this.commands.find(c => c.id === id)).filter(Boolean);
      const rest = this.commands.filter(c => !recent.includes(c.id));
      matches = [...recentCmds.map(c => ({...c, isRecent: true})), ...rest];
    }
    this.filteredCommands = matches;
    this.results.innerHTML = matches.map((c, i) => `
      <div class="command-palette-item ${i === this.selectedIndex ? 'selected' : ''} ${c.isRecent ? 'recent' : ''}" data-id="${c.id}" data-index="${i}">
        <span class="command-palette-icon">${c.icon || '⚡'}</span>
        <span class="command-palette-title">${escapeHtml(c.title)}</span>
        <span class="command-palette-shortcut">${c.isRecent ? '↺ recent' : escapeHtml(c.shortcut)}</span>
      </div>
    `).join('');
    this.results.querySelectorAll('.command-palette-item').forEach(item => {
      item.addEventListener('click', () => {
        const cmd = this.commands.find(c => c.id === item.dataset.id);
        if (cmd) { this.close(); this.saveRecent(cmd.id); cmd.run(); }
      });
      item.addEventListener('mouseenter', () => {
        this.selectedIndex = parseInt(item.dataset.index);
        this.highlightSelected();
      });
    });
  },
  
  highlightSelected() {
    this.results.querySelectorAll('.command-palette-item').forEach((item, i) => {
      item.classList.toggle('selected', i === this.selectedIndex);
    });
    // Scroll selected into view
    const selected = this.results.querySelector('.command-palette-item.selected');
    if (selected) selected.scrollIntoView({ block: 'nearest' });
  },
  
  getRecent() {
    try { return JSON.parse(localStorage.getItem(this.RECENT_KEY) || '[]').slice(0, 3); }
    catch { return []; }
  },
  
  saveRecent(id) {
    try {
      let recent = this.getRecent().filter(r => r !== id);
      recent.unshift(id);
      localStorage.setItem(this.RECENT_KEY, JSON.stringify(recent.slice(0, 5)));
    } catch { /* ignore */ }
  },
  
  async runNatural(q) {
    this.close();
    this.saveRecent('__natural__');
    if (typeof UI !== 'undefined') UI.toast('Agent', `Running: ${q}`, 'info');
    try {
      const r = await fetch('/api/agent/command', {
        method: 'POST',
        headers: { ...this.authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ directive: q })
      });
      const data = await r.json();
      const title = data.intent ? `Agent: ${data.intent}` : 'Agent Result';
      if (typeof UI !== 'undefined') UI.modal(title, `<pre class="log-output">${JSON.stringify(data, null, 2)}</pre>`);
      if (typeof logActivity === 'function') logActivity(`Agent: ${q}`, 'success', 12);
      if (typeof UI !== 'undefined') UI.toast('Agent', 'Done', 'success');
      EpicCommandCenter.refreshHUD();
    } catch (e) {
      if (typeof UI !== 'undefined') UI.toast('Agent Failed', e.message || String(e), 'error');
    }
  }
};

window.EpicCommandCenter = EpicCommandCenter;
window.CommandPalette = CommandPalette;
