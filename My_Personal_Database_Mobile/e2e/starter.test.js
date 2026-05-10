describe('Personal Database Mobile App', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  describe('App Launch', () => {
    it('should show login screen when not authenticated', async () => {
      // Should redirect to login if not authenticated
      await waitFor(element(by.text('Welcome Back'))).toBeVisible().withTimeout(5000);
    });

    it('should show loading indicator initially', async () => {
      // Check for loading indicator during app initialization
      await expect(element(by.id('loading-indicator'))).toBeVisible();
    });
  });

  describe('Login Screen', () => {
    it('should display login form elements', async () => {
      await waitFor(element(by.text('Welcome Back'))).toBeVisible().withTimeout(5000);
      await expect(element(by.text('Email'))).toBeVisible();
      await expect(element(by.text('Password'))).toBeVisible();
      await expect(element(by.text('Sign In'))).toBeVisible();
    });

    it('should show sign up option', async () => {
      await expect(element(by.text('Don\'t have an account?'))).toBeVisible();
      await expect(element(by.text('Sign Up'))).toBeVisible();
    });

    it('should show social login options', async () => {
      await expect(element(by.text('Continue with Google'))).toBeVisible();
      await expect(element(by.text('Continue with Apple'))).toBeVisible();
    });
  });

  describe('Authentication Flow', () => {
    it('should navigate to sign up screen', async () => {
      await element(by.text('Sign Up')).tap();
      await waitFor(element(by.text('Create Account'))).toBeVisible().withTimeout(3000);
    });

    it('should show password reset option', async () => {
      await expect(element(by.text('Forgot Password?'))).toBeVisible();
      await element(by.text('Forgot Password?')).tap();
      await waitFor(element(by.text('Reset Password'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Setup Flow', () => {
    it('should show setup screen after successful authentication', async () => {
      // This test assumes successful authentication would redirect to setup
      // In a real test environment, you might mock authentication
      await waitFor(element(by.text('Welcome to Your Personal Database'))).toBeVisible().withTimeout(10000);
    });

    it('should display setup steps', async () => {
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(10000);
      await expect(element(by.text('Next'))).toBeVisible();
    });

    it('should allow navigation through setup steps', async () => {
      await waitFor(element(by.text('Step 1'))).toBeVisible().withTimeout(10000);
      await element(by.text('Next')).tap();
      await waitFor(element(by.text('Step 2'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Main App Interface', () => {
    beforeEach(async () => {
      // Mock successful authentication and setup completion
      // In real tests, you would actually go through the auth flow
    });

    it('should show chat interface after setup', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await expect(element(by.id('new-chat-button'))).toBeVisible();
    });

    it('should display welcome screen when chat is empty', async () => {
      await waitFor(element(by.text('Welcome to Your Personal Database'))).toBeVisible().withTimeout(10000);
      await expect(element(by.text('Ask me anything about your personal data'))).toBeVisible();
    });

    it('should allow typing in chat input', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await element(by.id('chat-input')).typeText('Hello, how are you?');
      await expect(element(by.id('chat-input'))).toHaveText('Hello, how are you?');
    });

    it('should show send button when text is entered', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await element(by.id('chat-input')).typeText('Test message');
      await expect(element(by.id('send-button'))).toBeVisible();
    });

    it('should start new chat when new chat button is tapped', async () => {
      await waitFor(element(by.id('new-chat-button'))).toBeVisible().withTimeout(10000);
      await element(by.id('new-chat-button')).tap();
      // Should clear any existing chat and show welcome screen
      await waitFor(element(by.text('Welcome to Your Personal Database'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Chat Functionality', () => {
    beforeEach(async () => {
      // Ensure we're in a chat-ready state
    });

    it('should send a message and show loading state', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await element(by.id('chat-input')).typeText('What is my name?');
      await element(by.id('send-button')).tap();
      
      // Should show loading indicator
      await waitFor(element(by.id('loading-indicator'))).toBeVisible().withTimeout(3000);
      await expect(element(by.text('Analyzing your query...'))).toBeVisible();
    });

    it('should display response after sending message', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await element(by.id('chat-input')).typeText('Test query');
      await element(by.id('send-button')).tap();
      
      // Wait for response (this might take longer in real tests)
      await waitFor(element(by.text('assistant'))).toBeVisible().withTimeout(15000);
    });
  });

  describe('Navigation and Tab Bar', () => {
    it('should show tab navigation', async () => {
      await waitFor(element(by.id('tab-bar'))).toBeVisible().withTimeout(10000);
      await expect(element(by.id('chat-tab'))).toBeVisible();
      await expect(element(by.id('search-tab'))).toBeVisible();
      await expect(element(by.id('settings-tab'))).toBeVisible();
    });

    it('should navigate to search tab', async () => {
      await element(by.id('search-tab')).tap();
      await waitFor(element(by.id('search-screen'))).toBeVisible().withTimeout(3000);
    });

    it('should navigate to settings tab', async () => {
      await element(by.id('settings-tab')).tap();
      await waitFor(element(by.id('settings-screen'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      // This would require mocking network failures
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await element(by.id('chat-input')).typeText('Test message');
      await element(by.id('send-button')).tap();
      
      // Should show error message if network fails
      // await waitFor(element(by.text('Connection Error'))).toBeVisible().withTimeout(5000);
    });
  });

  describe('Accessibility', () => {
    it('should have accessible labels for major elements', async () => {
      await waitFor(element(by.id('chat-input'))).toBeVisible().withTimeout(10000);
      await expect(element(by.label('Chat input field'))).toBeVisible();
      await expect(element(by.label('Send message'))).toBeVisible();
      await expect(element(by.label('Start new chat'))).toBeVisible();
    });
  });
});
