const { chromium } = require('/home/scott/node_modules/playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dashboardUrl = process.env.DASHBOARD_URL || 'http://127.0.0.1:8000/dashboard';
  const landingUrl = 'http://127.0.0.1:8000/';
  const screenshotDir = '/home/scott/ai-lab/dashboard/landing/screenshots/';
  fs.mkdirSync(screenshotDir, { recursive: true });
  
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || '/snap/bin/chromium',
    args: ['--no-sandbox', '--disable-web-security'],
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  // First: capture the landing page
  try {
    await page.goto(landingUrl, { timeout: 30000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(screenshotDir, 'landing.png') });
    console.log('Landing page: OK');
  } catch (e) {
    console.error('Landing page: FAILED - ' + e.message);
  }
  
  // Second: capture dashboard panels
  try {
    await page.goto(dashboardUrl, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    
    // Click Epic HUD button to show modal
    const panels = [
      { selector: 'button[data-action="powerups"]', id: 'epic-hud', label: 'Epic HUD' },
      { selector: 'button[data-action="gpu"]', id: 'gpu-status', label: 'GPU Status' },
      { selector: 'button[data-action="disk"]', id: 'disk-rescue', label: 'Disk Rescue' },
      { selector: 'button[data-action="models"]', id: 'model-truth', label: 'Model Truth' },
    ];
    
    for (const panel of panels) {
      try {
        const btn = await page.$(panel.selector);
        if (btn) {
          await btn.click();
          await page.waitForSelector('#modal-overlay:not(.hidden)', { timeout: 3000 });
          await page.screenshot({ path: path.join(screenshotDir, `${panel.id}.png`), fullPage: true });
          console.log(`${panel.label}: OK`);
          await page.keyboard.press('Escape');
          await page.waitForTimeout(200);
        }
      } catch (e) {
        console.error(`${panel.label}: FAILED - ${e.message}`);
      }
    }
  } catch (e) {
    console.error('Dashboard: FAILED - ' + e.message);
  }
  
  await browser.close();
  console.log(`\nDone. Screenshots saved to: ${screenshotDir}`);
})();