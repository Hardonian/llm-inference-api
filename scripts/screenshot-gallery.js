const { chromium } = require('/home/scott/node_modules/playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dashboardUrl = process.env.DASHBOARD_URL || 'http://127.0.0.1:8000/dashboard';
  const screenshotDir = '/home/scott/ai-lab/dashboard/landing/screenshots/';
  fs.mkdirSync(screenshotDir, { recursive: true });
  
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || '/snap/bin/chromium',
    args: ['--no-sandbox'],
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  let page = await context.newPage();
  
  // Panel definitions for screenshots
  const panels = [
    { id: 'epic-hud', label: 'Epic HUD', selector: '[data-action="powerups"]' },
    { id: 'gpu-status', label: 'GPU Status', selector: '[data-action="gpu"]' },
    { id: 'disk-rescue', label: 'Disk Rescue', selector: '[data-action="disk"]' },
    { id: 'model-truth', label: 'Model Truth', selector: '[data-action="models"]' },
    { id: 'comfyui', label: 'ComfyUI', selector: '[data-action="comfy"]' },
    { id: 'security', label: 'Security', selector: '[data-action="security"]' },
    { id: 'tools', label: 'Tools', selector: '[data-action="tools"]' },
    { id: 'powerups', label: 'Powerups', selector: '[data-action="powerups"]' },
  ];
  
  console.log(`Capturing ${panels.length} panel screenshots...`);
  
  for (const panel of panels) {
    try {
      // Open panel
      await page.evaluate(() => {
        window.UI?.closeModal?.();
        document.getElementById('modal-overlay')?.classList.add('hidden');
      }).catch(() => {});
      
      await page.locator(panel.selector).waitFor({ state: 'attached', timeout: 10000 });
      await page.evaluate((sel) => document.querySelector(sel)?.click(), panel.selector);
      await page.waitForSelector('#modal-overlay:not(.hidden)', { timeout: 10000 });
      
      // Take screenshot
      const filepath = path.join(screenshotDir, `${panel.id}.png`);
      await page.screenshot({ path: filepath, fullPage: true });
      console.log(`${panel.label}: captured to ${filepath}`);
      
      // Close modal
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(300);
    } catch (e) {
      console.error(`${panel.label}: FAILED - ${e.message}`);
    }
  }
  
  // Also capture the landing page (root route)
  try {
    await page.goto(dashboardUrl, { timeout: 30000 });
    const landingPath = path.join(screenshotDir, 'landing.png');
    await page.screenshot({ path: landingPath });
    console.log('Landing page: captured to ' + landingPath);
  } catch (e) {
    console.error('Landing page: FAILED - ' + e.message);
  }
  
  await browser.close();
  console.log(`\nScreenshot gallery saved to: ${screenshotDir}`);
})();