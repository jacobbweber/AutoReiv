import { test, expect } from '@playwright/test';

/**
 * Playwright Smoke Test Gate [REQ-FE-005]
 * Verifies that the AutoReiv Web Single-Page Application loads cleanly
 * with zero uncaught console errors and that core navigation tabs are rendered in the DOM.
 */
test.describe('AutoReiv Web SPA Smoke Gate', () => {
  test('initial page load emits zero console errors and renders core studio tabs', async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];

    // Intercept console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Intercept unhandled window errors / exceptions
    page.on('pageerror', (exception) => {
      pageErrors.push(exception.message);
    });

    // Navigate to root
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);

    // Verify main navigation studio tabs exist
    await expect(page.locator('#tab-chat')).toBeAttached();
    await expect(page.locator('#tab-wiki')).toBeAttached();
    await expect(page.locator('#tab-agents')).toBeAttached();
    await expect(page.locator('#tab-settings')).toBeAttached();
    await expect(page.locator('#tab-observability')).toBeAttached();
    await expect(page.locator('#tab-docs')).toBeAttached();
    await expect(page.locator('#tab-routines')).toBeAttached();

    // Verify main views exist
    await expect(page.locator('#view-chat')).toBeAttached();
    await expect(page.locator('#view-wiki')).toBeAttached();
    await expect(page.locator('#view-agents')).toBeAttached();
    await expect(page.locator('#view-settings')).toBeAttached();
    await expect(page.locator('#view-observability')).toBeAttached();
    await expect(page.locator('#view-docs')).toBeAttached();
    await expect(page.locator('#view-routines')).toBeAttached();

    // Assert zero uncaught page errors or console errors
    expect(pageErrors, `Uncaught page errors detected: ${pageErrors.join(', ')}`).toEqual([]);
    expect(consoleErrors, `Console errors detected: ${consoleErrors.join(', ')}`).toEqual([]);
  });

  test('clicking each studio tab switches views with zero console errors', async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (exception) => pageErrors.push(exception.message));

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const tabs = [
      { id: '#tab-routines', viewId: '#view-routines' },
      { id: '#tab-observability', viewId: '#view-observability' },
      { id: '#tab-agents', viewId: '#view-agents' },
      { id: '#tab-settings', viewId: '#view-settings' },
      { id: '#tab-docs', viewId: '#view-docs' },
      { id: '#tab-wiki', viewId: '#view-wiki' },
      { id: '#tab-chat', viewId: '#view-chat' },
    ];

    for (const tab of tabs) {
      await page.locator(tab.id).click();
      await expect(page.locator(tab.viewId)).toBeVisible();
    }

    expect(pageErrors, `Uncaught page errors detected during navigation: ${pageErrors.join(', ')}`).toEqual([]);
    expect(consoleErrors, `Console errors detected during navigation: ${consoleErrors.join(', ')}`).toEqual([]);
  });
});

