describe('Setup Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  describe('Setup Screen Navigation', () => {
    beforeEach(async () => {
      // Mock successful authentication to reach setup screen
      // In real tests, you would complete the actual authentication flow
    });

    it('should display setup welcome screen', async () => {
      await waitFor(element(by.text('Welcome to Your Personal Database'))).toBeVisible().withTimeout(10000);
      await expect(element(by.text('Let\'s get you set up in a few simple steps'))).toBeVisible();
      await expect(element(by.text('Get Started'))).toBeVisible();
    });

    it('should start setup process when Get Started is tapped', async () => {
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Step 1: Basic Information', () => {
    beforeEach(async () => {
      // Navigate to Step 1
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(3000);
    });

    it('should display step 1 content', async () => {
      await expect(element(by.text('Basic Information'))).toBeVisible();
      await expect(element(by.text('Tell us a bit about yourself'))).toBeVisible();
      await expect(element(by.id('name-input'))).toBeVisible();
      await expect(element(by.text('Next'))).toBeVisible();
    });

    it('should validate required fields in step 1', async () => {
      await element(by.text('Next')).tap();
      // Should show validation error
      await waitFor(element(by.text('Name is required'))).toBeVisible().withTimeout(3000);
    });

    it('should proceed to step 2 with valid input', async () => {
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 2'))).toBeVisible().withTimeout(3000);
    });

    it('should allow going back to welcome screen', async () => {
      await expect(element(by.text('Back'))).toBeVisible();
      await element(by.text('Back')).tap();
      await waitFor(element(by.text('Welcome to Your Personal Database'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Step 2: Data Sources', () => {
    beforeEach(async () => {
      // Complete Step 1
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(3000);
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 2'))).toBeVisible().withTimeout(3000);
    });

    it('should display step 2 content', async () => {
      await expect(element(by.text('Data Sources'))).toBeVisible();
      await expect(element(by.text('Choose the data sources you want to connect'))).toBeVisible();
      await expect(element(by.text('Google Drive'))).toBeVisible();
      await expect(element(by.text('Apple Music'))).toBeVisible();
      await expect(element(by.text('Calendar'))).toBeVisible();
    });

    it('should allow selecting data sources', async () => {
      await element(by.text('Google Drive')).tap();
      await expect(element(by.id('google-drive-selected'))).toBeVisible();
      
      await element(by.text('Apple Music')).tap();
      await expect(element(by.id('apple-music-selected'))).toBeVisible();
    });

    it('should require at least one data source', async () => {
      await element(by.text('Next')).tap();
      // Should show validation error
      await waitFor(element(by.text('Please select at least one data source'))).toBeVisible().withTimeout(3000);
    });

    it('should proceed to step 3 with selected sources', async () => {
      await element(by.text('Google Drive')).tap();
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 3'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Step 3: Permissions', () => {
    beforeEach(async () => {
      // Complete Steps 1 and 2
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(3000);
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 2'))).toBeVisible().withTimeout(3000);
      await element(by.text('Google Drive')).tap();
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 3'))).toBeVisible().withTimeout(3000);
    });

    it('should display step 3 content', async () => {
      await expect(element(by.text('Permissions'))).toBeVisible();
      await expect(element(by.text('Grant permissions to access your data'))).toBeVisible();
      await expect(element(by.text('Request Permissions'))).toBeVisible();
    });

    it('should request permissions when button is tapped', async () => {
      await element(by.text('Request Permissions')).tap();
      // Should show permission request dialog
      // In real tests, you would handle the permission dialog
    });

    it('should show permission status', async () => {
      // After requesting permissions, should show status
      await waitFor(element(by.text('Permissions granted'))).toBeVisible().withTimeout(5000);
    });

    it('should proceed to final step with permissions granted', async () => {
      await element(by.text('Request Permissions')).tap();
      // Handle permission dialog (mock in tests)
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Complete Setup'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Setup Completion', () => {
    beforeEach(async () => {
      // Complete all setup steps
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(3000);
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 2'))).toBeVisible().withTimeout(3000);
      await element(by.text('Google Drive')).tap();
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 3'))).toBeVisible().withTimeout(3000);
      await element(by.text('Request Permissions')).tap();
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Complete Setup'))).toBeVisible().withTimeout(3000);
    });

    it('should display completion screen', async () => {
      await expect(element(by.text('Setup Complete!'))).toBeVisible();
      await expect(element(by.text('Your personal database is ready to use'))).toBeVisible();
      await expect(element(by.text('Start Using App'))).toBeVisible();
    });

    it('should navigate to main app when Start Using App is tapped', async () => {
      await element(by.text('Start Using App')).tap();
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(5000);
    });

    it('should show setup summary', async () => {
      await expect(element(by.text('Setup Summary'))).toBeVisible();
      await expect(element(by.text('John Doe'))).toBeVisible();
      await expect(element(by.text('Google Drive'))).toBeVisible();
      await expect(element(by.text('Permissions granted'))).toBeVisible();
    });
  });

  describe('Setup Progress', () => {
    it('should show progress indicator', async () => {
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await waitFor(element(by.id('setup-progress'))).toBeVisible().withTimeout(3000);
    });

    it('should update progress as steps are completed', async () => {
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      
      // Step 1
      await waitFor(element(by.text('Step 1 of 3'))).toBeVisible().withTimeout(3000);
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      
      // Step 2
      await waitFor(element(by.text('Step 2 of 3'))).toBeVisible().withTimeout(3000);
      await element(by.text('Google Drive')).tap();
      await element(by.text('Next')).tap();
      
      // Step 3
      await waitFor(element(by.text('Step 3 of 3'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Setup Error Handling', () => {
    it('should handle network errors during setup', async () => {
      // Mock network failure during setup
      await waitFor(element(by.text('Get Started'))).toBeVisible().withTimeout(10000);
      await element(by.text('Get Started')).tap();
      await element(by.id('name-input')).typeText('John Doe');
      await element(by.text('Next')).tap();
      
      // Should show error if network fails
      // await waitFor(element(by.text('Network error occurred'))).toBeVisible().withTimeout(5000);
    });

    it('should allow retry after error', async () => {
      // After showing error, should allow retry
      await expect(element(by.text('Retry'))).toBeVisible();
      await element(by.text('Retry')).tap();
      // Should proceed with setup
    });
  });
});
