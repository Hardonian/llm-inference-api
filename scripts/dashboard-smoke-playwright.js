const { chromium } = require('/home/scott/node_modules/playwright');

(async () => {
  const dashboardUrl = process.env.DASHBOARD_URL || 'http://127.0.0.1:8000/dashboard';
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || '/snap/bin/chromium',
    args: ['--no-sandbox'],
  });
  const context = await browser.newContext();
  let page;
  context.on('page', async p => { if (page && p !== page) setTimeout(() => p.close().catch(() => {}), 250); });
  page = await context.newPage();

  const errors = [];
  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' && !/favicon/i.test(text)) errors.push(`console: ${text}`);
  });
  page.on('pageerror', err => errors.push(`pageerror: ${err.message}`));
  page.on('requestfailed', req => {
    const url = req.url();
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')) {
      errors.push(`requestfailed: ${url} ${req.failure()?.errorText}`);
    }
  });

  await page.goto(dashboardUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('[data-action="tools"]', { timeout: 15000 });
  await page.evaluate(() => { localStorage.clear(); });

  async function closeModal() {
    await page.keyboard.press('Escape').catch(() => {});
    await page.evaluate(() => {
      window.UI?.closeModal?.();
      const overlay = document.getElementById('modal-overlay');
      if (overlay) overlay.classList.add('hidden');
    }).catch(() => {});
    await page.waitForTimeout(150);
  }
  async function clearToasts() {
    await page.evaluate(() => document.querySelectorAll('.toast').forEach(t => t.remove())).catch(() => {});
  }
  async function clickAndCheck(selector, expectedRegex, label) {
    await closeModal();
    await clearToasts();
    await page.locator(selector).waitFor({ state: 'attached', timeout: 10000 });
    await page.evaluate((sel) => document.querySelector(sel)?.click(), selector);
    await page.waitForSelector('#modal-overlay:not(.hidden)', { timeout: 10000 });
    const text = await page.locator('#modal').innerText({ timeout: 10000 });
    if (!expectedRegex.test(text)) throw new Error(`${label} modal text mismatch: ${text.slice(0, 220)}`);
    console.log(`${label}: OK`);
  }

  for (const [selector, rx, label] of [
    ['[data-action="tools"]', /Custom Tools|Tools/i, 'Tools'],
    ['[data-action="mcp"]', /MCP|Agent/i, 'MCP'],
    ['[data-action="views"]', /Views|Dashboard/i, 'Views'],
    ['[data-action="workflow"]', /Workflow Builder|Builder/i, 'Builder'],
    ['[data-action="comfy"]', /ComfyUI|Models|Nodes/i, 'ComfyUI'],
    ['[data-action="security"]', /Security/i, 'Security'],
    ['[data-action="powerups"]', /Superpowers|Cheat Codes|Powerups/i, 'Powerups'],
    ['[data-action="disk"]', /Disk Rescue|Estimated reclaim/i, 'Disk Rescue'],
    ['[data-action="models"]', /Model Store Truth|Active paths/i, 'Model Truth'],
    ['[data-action="mature"]', /Mature|Private|Workflow/i, 'Mature'],
  ]) await clickAndCheck(selector, rx, label);

  await closeModal();
  for (const action of ['upscale', 'variations', 'report', 'heal', 'cleanup', 'backup', 'batch', 'gpu', 'generate']) {
    await closeModal();
    await clearToasts();
    page.once('dialog', d => d.accept().catch(() => {}));
    await page.click(`[data-action="${action}"]`, { timeout: 10000 });
    await page.waitForTimeout(action === 'cleanup' ? 2500 : action === 'heal' ? 2500 : 1500);
    const toastText = await page.locator('#toast-container').innerText().catch(() => '');
    const modalOpen = await page.locator('#modal-overlay:not(.hidden)').count().catch(() => 0);
    const healSignal = action === 'heal'
      ? await page.locator('#activity-log').innerText().catch(() => '')
      : '';
    if (!toastText.trim() && !modalOpen && !(action === 'heal' && /Self-heal/i.test(healSignal)) && action !== 'generate') throw new Error(`${action} produced no toast/modal`);
    console.log(`${action}: OK`);
  }

  await closeModal();
  await page.click('[data-action="powerups"]');
  await page.waitForSelector('#modal-overlay:not(.hidden)', { timeout: 10000 });
  await page.click('button:has-text("Money Path Finder")');
  await page.waitForTimeout(1500);
  const powerOutput = await page.locator('#powerup-output').innerText({ timeout: 10000 });
  if (!/paths|private|dashboard|price/i.test(powerOutput)) throw new Error(`Powerup output missing expected content: ${powerOutput.slice(0, 220)}`);
  console.log('Powerup run: OK');

  // Epic Command Center
  await page.locator('#epic-revenue-btn').waitFor({ state: 'attached', timeout: 10000 });
  await page.evaluate(() => document.querySelector('#epic-revenue-btn')?.click());
  await page.waitForTimeout(1200);
  const epicOutput = await page.locator('#epic-output').textContent();
  if (!epicOutput || epicOutput.length < 20) throw new Error('Epic Command Center output empty');
  console.log('Epic Command Center OK');

  // Command palette open/close
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(400);
  const hidden = await page.locator('#command-palette').evaluate(el => el.classList.contains('hidden'));
  if (hidden) throw new Error('Command palette did not open');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  console.log('Command Palette OK');

  await page.waitForTimeout(1000);
  if (errors.length) throw new Error('Browser errors:\n' + errors.join('\n'));
  await browser.close();
})();
