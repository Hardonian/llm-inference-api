(() => {
  const $ = (id) => document.getElementById(id);

  function numberValue(id, fallback) {
    const value = Number($(id)?.value);
    return Number.isFinite(value) ? value : fallback;
  }

  function renderResult(data) {
    const verdictClass = data.verdict === 'scale' ? 'risk-low' : data.verdict === 'optimize' ? 'risk-medium' : 'risk-critical';
    return `
      <div class="epic-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">
        <div class="epic-card"><div class="epic-label">TVY / Run</div><div class="epic-value ${verdictClass}">${data.true_value_yield_min}m</div><div class="epic-sub">${data.source}</div></div>
        <div class="epic-card"><div class="epic-label">Value / Run</div><div class="epic-value">$${data.value_usd_per_run}</div><div class="epic-sub">time-value adjusted</div></div>
        <div class="epic-card"><div class="epic-label">Monthly Value</div><div class="epic-value">$${data.monthly_value_usd}</div><div class="epic-sub">projected</div></div>
        <div class="epic-card"><div class="epic-label">Verdict</div><div class="epic-value ${verdictClass}">${data.verdict}</div><div class="epic-sub">${data.next_action}</div></div>
      </div>
      <pre style="white-space:pre-wrap;margin-top:10px">${JSON.stringify(data, null, 2)}</pre>
    `;
  }

  async function calculate() {
    const result = $('apva-result');
    if (!result) return;
    result.textContent = 'Calculating APVA True Value Yield...';
    const payload = {
      name: $('apva-name')?.value || 'workflow',
      human_baseline_min: numberValue('apva-human', 60),
      ai_generation_time_min: numberValue('apva-ai', 5),
      verification_time_min: numberValue('apva-verify', 8),
      skill_level: $('apva-skill')?.value || 'mid',
      exact_span_recall: 0.9,
      faithfulness_score: 0.85,
      base_latency_overhead_min: 0.5,
      false_positive_rate: 0.05,
      resolution_penalty_min: 10,
      cra_session_drop_penalty_min: 1,
      hourly_value_usd: 75,
      monthly_runs: numberValue('apva-runs', 20),
    };
    try {
      const authHeaders = window.CommandPalette?.authHeaders?.() || {};
      const response = await fetch('/api/productivity/apva', {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || response.statusText);
      result.innerHTML = renderResult(data);
      if (window.UI?.toast) window.UI.toast('APVA calculated', `${data.verdict}: ${data.true_value_yield_min}m TVY/run`, data.is_net_positive ? 'success' : 'warning');
    } catch (error) {
      result.textContent = `APVA calculation failed: ${error.message || error}`;
    }
  }

  function loadDemo() {
    if ($('apva-name')) $('apva-name').value = 'Productized AI Lab Audit';
    if ($('apva-human')) $('apva-human').value = '180';
    if ($('apva-ai')) $('apva-ai').value = '25';
    if ($('apva-verify')) $('apva-verify').value = '30';
    if ($('apva-skill')) $('apva-skill').value = 'mid';
    if ($('apva-runs')) $('apva-runs').value = '12';
    calculate();
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('apva-run')?.addEventListener('click', calculate);
    $('apva-load-demo')?.addEventListener('click', loadDemo);
    calculate();
  });
})();
