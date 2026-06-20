(() => {
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));

  async function loadNextAction() {
    const target = $('operator-result');
    if (!target) return;
    target.textContent = 'Loading next best action...';
    try {
      const headers = window.CommandPalette?.authHeaders?.() || {};
      const response = await fetch('/api/operator/next-action', { headers });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || response.statusText);
      const repos = (data.repos || []).map((repo) => `
        <div class="epic-card" style="margin-top:8px">
          <div class="epic-label">${escapeHtml(repo.name)} repo</div>
          <div class="epic-value ${repo.dirty_files ? 'risk-medium' : 'risk-low'}">${repo.dirty_files} dirty</div>
          <div class="epic-sub">${escapeHtml(repo.branch)} • ${escapeHtml(repo.path)}</div>
        </div>`).join('');
      target.innerHTML = `
        <div class="epic-card">
          <div class="epic-label">Do First</div>
          <div class="epic-value">${escapeHtml(data.top_action)}</div>
          <div class="epic-sub">${escapeHtml(data.why)}</div>
        </div>
        <pre style="white-space:pre-wrap;margin-top:10px">Expected value: ${escapeHtml(data.expected_value)}\nRisk: ${escapeHtml(data.risk)}\nCommand: ${escapeHtml(data.command)}\nVerify: ${escapeHtml(data.verify)}\nIgnore: ${escapeHtml((data.ignore || []).join(', '))}</pre>
        ${repos}`;
    } catch (error) {
      target.textContent = `Next-action load failed: ${error.message || error}`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('operator-refresh')?.addEventListener('click', loadNextAction);
    loadNextAction();
  });
})();
