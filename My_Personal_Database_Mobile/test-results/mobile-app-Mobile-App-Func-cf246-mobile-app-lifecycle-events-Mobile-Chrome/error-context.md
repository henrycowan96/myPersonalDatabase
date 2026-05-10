# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: mobile-app.spec.ts >> Mobile App Functionality >> should handle mobile app lifecycle events
- Location: e2e/mobile-app.spec.ts:177:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:8081/
Call log:
  - navigating to "http://localhost:8081/", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Mobile App Functionality', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     // Set viewport to mobile size
  6   |     await page.setViewportSize({ width: 375, height: 667 });
  7   |     
  8   |     // Navigate to the mobile app (assuming it's running on localhost:8081)
> 9   |     await page.goto('http://localhost:8081');
      |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:8081/
  10  |     
  11  |     // Wait for the app to load
  12  |     await page.waitForTimeout(3000);
  13  |   });
  14  | 
  15  |   test('should load the mobile app', async ({ page }) => {
  16  |     // Check that the app container is visible
  17  |     await expect(page.locator('body')).toBeVisible();
  18  |     
  19  |     // Take a screenshot for debugging
  20  |     await page.screenshot({ path: 'mobile-app-loaded.png' });
  21  |   });
  22  | 
  23  |   test('should display app navigation', async ({ page }) => {
  24  |     // Look for common mobile navigation elements
  25  |     const navigationSelectors = [
  26  |       '[data-testid="tab-bar"]',
  27  |       '[data-testid="navigation"]',
  28  |       'nav',
  29  |       '.tab-bar',
  30  |       '.navigation'
  31  |     ];
  32  |     
  33  |     let navigationFound = false;
  34  |     for (const selector of navigationSelectors) {
  35  |       try {
  36  |         await expect(page.locator(selector)).toBeVisible({ timeout: 5000 });
  37  |         navigationFound = true;
  38  |         break;
  39  |       } catch (error) {
  40  |         // Continue to next selector
  41  |       }
  42  |     }
  43  |     
  44  |     if (!navigationFound) {
  45  |       // Take screenshot to see what's actually displayed
  46  |       await page.screenshot({ path: 'mobile-navigation-debug.png' });
  47  |       console.log('Navigation elements not found, screenshot saved for debugging');
  48  |     }
  49  |   });
  50  | 
  51  |   test('should handle mobile touch interactions', async ({ page }) => {
  52  |     // Test touch interactions
  53  |     await page.touchscreen.tap(100, 100);
  54  |     
  55  |     // Wait for any response
  56  |     await page.waitForTimeout(1000);
  57  |     
  58  |     // Take screenshot after tap
  59  |     await page.screenshot({ path: 'mobile-tap-interaction.png' });
  60  |   });
  61  | 
  62  |   test('should be responsive to different screen sizes', async ({ page }) => {
  63  |     // Test different mobile screen sizes
  64  |     const screenSizes = [
  65  |       { width: 375, height: 667 }, // iPhone SE
  66  |       { width: 414, height: 896 }, // iPhone 11
  67  |       { width: 360, height: 640 }, // Android
  68  |     ];
  69  |     
  70  |     for (const size of screenSizes) {
  71  |       await page.setViewportSize(size);
  72  |       await page.waitForTimeout(1000);
  73  |       
  74  |       // Take screenshot for each size
  75  |       await page.screenshot({ 
  76  |         path: `mobile-screen-${size.width}x${size.height}.png` 
  77  |       });
  78  |       
  79  |       // Check that content is still visible
  80  |       await expect(page.locator('body')).toBeVisible();
  81  |     }
  82  |   });
  83  | 
  84  |   test('should handle mobile gestures', async ({ page }) => {
  85  |     // Test basic touch interactions
  86  |     await page.touchscreen.tap(100, 300);
  87  |     
  88  |     await page.waitForTimeout(1000);
  89  |     await page.screenshot({ path: 'mobile-touch-gesture.png' });
  90  |   });
  91  | 
  92  |   test('should work with mobile device emulation', async ({ page }) => {
  93  |     // Test with specific mobile device emulation
  94  |     const devices = ['iPhone 12', 'Pixel 5'];
  95  |     
  96  |     for (const device of devices) {
  97  |       const context = await page.context();
  98  |       await context.addCookies([{
  99  |         name: 'device_test',
  100 |         value: device,
  101 |         domain: 'localhost',
  102 |         path: '/'
  103 |       }]);
  104 |       
  105 |       await page.reload();
  106 |       await page.waitForTimeout(2000);
  107 |       
  108 |       await page.screenshot({ 
  109 |         path: `mobile-device-${device.toLowerCase().replace(' ', '-')}.png` 
```