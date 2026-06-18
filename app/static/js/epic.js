// Epic / Breaker Powerups Module for AI Lab Command Center
// Loaded as a separate module to avoid main dashboard bloat.

if (typeof escapeHtml !== 'function') {
  window.escapeHtml = function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  };
}

const EpicCommandCenter = {
  output: null,
  init() {
    this.output = document.getElementById('epic-output');
    document.getElementById('epic-revenue-btn')?.addEventListener('click', () => this.run('revenue'));
    document.getElementById('epic-predict-btn')?.addEventListener('click', () => this.run('predictions'));
    document.getElementById('epic-improve-btn')?.addEventListener('click', () => this.run('improvements'));
    document.getElementById('epic-packs-btn')?.addEventListener('click', () => this.run('packs'));
    document.getElementById('epic-command-btn')?.addEventListener('click', () => CommandPalette.open());
    this.refreshHUD();
    setInterval(() => this.refreshHUD(), 30000);
  },
  write(value) {
    if (!this.output) return;
    this.output.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  },
  async refreshHUD() {
    try {
      const [rev, pred, imp, packs] = await Promise.allSettled([
        API.revenue(), API.predictions(), API.improvements(), API.workflowPacks()
      ]);
      if (rev.status === 'fulfilled') {
        const r = rev.value;
        document.getElementById('revenue-score').textContent = `${r.overall_readiness || 0}%`;
        document.getElementById('revenue-next').textContent = r.next_action || 'Scan revenue';
      }
      if (pred.status === 'fulfilled') {
        const p = pred.value.predictions?.[0];
        document.getElementById('prediction-risk').textContent = p?.risk?.toUpperCase() || '—';
        document.getElementById('prediction-days').textContent = p?.days_to_full ? `${p.days_to_full}d to full` : 'trend N/A';
      }
      if (imp.status === 'fulfilled') {
        const i = imp.value;
        document.getElementById('improve-count').textContent = i.suggestions?.length || 0;
        document.getElementById('improve-top').textContent = i.suggestions?.[0]?.title || '—';
      }
      if (packs.status === 'fulfilled') {
        const pk = packs.value;
        document.getElementById('packs-count').textContent = pk.ready_packs?.length || 0;
        document.getElementById('packs-top').textContent = pk.ready_packs?.[0]?.workflow || '—';
      }
    } catch (e) { console.warn('Epic HUD refresh failed', e); }
  },
  async run(kind) {
    if (!this.output) return;
    UI.toast('Epic', `Running ${kind}`, 'info');
    try {
      let result;
      if (kind === 'revenue') result = await API.revenue();
      else if (kind === 'predictions') result = await API.predictions();
      else if (kind === 'improvements') result = await API.improvements();
      else if (kind === 'packs') result = await API.workflowPacks();
      else result = await API.agentCommand(kind);
      this.write(result);
      logActivity(`Epic ${kind}`, 'success', 10);
      UI.toast('Epic Complete', kind, 'success');
    } catch (e) {
      this.write(e.message || String(e));
      UI.toast('Epic Failed', e.message || String(e), 'error');
    }
  }
};

const CommandPalette = {
  el: null,
  input: null,
  results: null,
  commands: [
    { id: 'heal', title: 'Heal Workstation', shortcut: 'heal', run: () => EpicCommandCenter.run('heal') },
    { id: 'money', title: 'Show Money Paths / Revenue', shortcut: 'money', run: () => EpicCommandCenter.run('revenue') },
    { id: 'disk', title: 'Disk Rescue Report', shortcut: 'disk rescue', run: () => DiskRescuePanel.open() },
    { id: 'models', title: 'Model Store Truth', shortcut: 'models', run: () => ModelTruthPanel.open() },
    { id: 'improve', title: 'Self-Improvement Suggestions', shortcut: 'improve', run: () => EpicCommandCenter.run('improvements') },
    { id: 'predict', title: 'Predictive Monitoring', shortcut: 'predict', run: () => EpicCommandCenter.run('predictions') },
    { id: 'packs', title: 'Workflow Product Packs', shortcut: 'packs', run: () => EpicCommandCenter.run('packs') },
    { id: 'brief', title: 'Operator Briefing', shortcut: 'brief', run: () => typeof runBriefing === 'function' && runBriefing() },
    { id: 'repos', title: 'Repo Radar', shortcut: 'repos', run: () => API.coopRepos().then(r => { UI.modal('Repo Radar', `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`); }) },
    { id: 'private', title: 'Private Creations', shortcut: 'private', run: () => API.privateCreations().then(r => { UI.modal('Private Creations', `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`); }) },
    { id: 'powerups', title: 'Open Powerups Panel', shortcut: 'powerups', run: () => PowerupsPanel.open() },
    { id: 'smoke', title: 'Run Dashboard Smoke', shortcut: 'smoke', run: () => API.runSmoke().then(r => UI.toast('Smoke', `${r.ok ? 'OK' : 'FAIL'}`, r.ok ? 'success' : 'error')) },
    { id: 'refresh', title: 'Refresh Dashboard', shortcut: 'refresh', run: () => typeof fetchInitialData === 'function' && fetchInitialData() },
    { id: 'theme', title: 'Toggle Theme', shortcut: 'theme', run: () => document.getElementById('theme-toggle')?.click() },
  ],
  init() {
    this.el = document.getElementById('command-palette');
    this.input = document.getElementById('command-palette-input');
    this.results = document.getElementById('command-palette-results');
    document.getElementById('command-palette-close')?.addEventListener('click', () => this.close());
    this.input?.addEventListener('input', () => this.render());
    this.input?.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.close();
      if (e.key === 'Enter') {
        const q = this.input.value.trim();
        this.runNatural(q);
      }
    });
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); this.open(); }
      if (e.key === 'Escape' && this.el && !this.el.classList.contains('hidden')) { this.close(); }
    });
  },
  open() {
    if (!this.el) return;
    this.el.classList.remove('hidden');
    this.input.value = '';
    this.input.focus();
    this.render();
  },
  close() {
    if (!this.el) return;
    this.el.classList.add('hidden');
  },
  render() {
    const q = (this.input.value || '').toLowerCase();
    const matches = q ? this.commands.filter(c => c.title.toLowerCase().includes(q) || c.shortcut.includes(q)) : this.commands;
    this.results.innerHTML = matches.map((c, i) => `
      <div class="command-palette-item ${i === 0 ? 'selected' : ''}" data-id="${c.id}">
        <span class="command-palette-title">${escapeHtml(c.title)}</span>
        <span class="command-palette-shortcut">${escapeHtml(c.shortcut)}</span>
      </div>
    `).join('');
    this.results.querySelectorAll('.command-palette-item').forEach(item => {
      item.addEventListener('click', () => {
        const cmd = this.commands.find(c => c.id === item.dataset.id);
        if (cmd) { this.close(); cmd.run(); }
      });
    });
  },
  async runNatural(q) {
    this.close();
    UI.toast('Agent', `Running: ${q}`, 'info');
    try {
      const r = await API.agentCommand(q);
      const title = r.intent ? `Agent: ${r.intent}` : 'Agent Result';
      UI.modal(title, `<pre class="log-output">${JSON.stringify(r, null, 2)}</pre>`);
      logActivity(`Agent: ${q}`, 'success', 12);
      UI.toast('Agent', 'Done', 'success');
      EpicCommandCenter.refreshHUD();
    } catch (e) {
      UI.toast('Agent Failed', e.message || String(e), 'error');
    }
  }
};

window.EpicCommandCenter = EpicCommandCenter;
window.CommandPalette = CommandPalette;
