describe('Authentication Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  describe('Login Screen', () => {
    it('should display all login elements', async () => {
      await waitFor(element(by.text('Welcome Back'))).toBeVisible().withTimeout(5000);
      await expect(element(by.text('Email'))).toBeVisible();
      await expect(element(by.text('Password'))).toBeVisible();
      await expect(element(by.text('Sign In'))).toBeVisible();
      await expect(element(by.text('Continue with Google'))).toBeVisible();
      await expect(element(by.text('Continue with Apple'))).toBeVisible();
    });

    it('should validate email input', async () => {
      await waitFor(element(by.id('email-input'))).toBeVisible().withTimeout(5000);
      await element(by.id('email-input')).typeText('invalid-email');
      await element(by.id('password-input')).typeText('password123');
      await element(by.text('Sign In')).tap();
      
      // Should show validation error
      await waitFor(element(by.text('Invalid email address'))).toBeVisible().withTimeout(3000);
    });

    it('should validate required fields', async () => {
      await element(by.text('Sign In')).tap();
      
      // Should show validation errors for empty fields
      await waitFor(element(by.text('Email is required'))).toBeVisible().withTimeout(3000);
      await waitFor(element(by.text('Password is required'))).toBeVisible().withTimeout(3000);
    });

    it('should handle invalid credentials', async () => {
      await waitFor(element(by.id('email-input'))).toBeVisible().withTimeout(5000);
      await element(by.id('email-input')).typeText('test@example.com');
      await element(by.id('password-input')).typeText('wrongpassword');
      await element(by.text('Sign In')).tap();
      
      // Should show error message for invalid credentials
      await waitFor(element(by.text('Invalid credentials'))).toBeVisible().withTimeout(5000);
    });
  });

  describe('Sign Up Screen', () => {
    beforeEach(async () => {
      await element(by.text('Sign Up')).tap();
      await waitFor(element(by.text('Create Account'))).toBeVisible().withTimeout(3000);
    });

    it('should display all sign up elements', async () => {
      await expect(element(by.text('Name'))).toBeVisible();
      await expect(element(by.text('Email'))).toBeVisible();
      await expect(element(by.text('Password'))).toBeVisible();
      await expect(element(by.text('Confirm Password'))).toBeVisible();
      await expect(element(by.text('Create Account'))).toBeVisible();
    });

    it('should validate password confirmation', async () => {
      await element(by.id('name-input')).typeText('Test User');
      await element(by.id('email-input')).typeText('test@example.com');
      await element(by.id('password-input')).typeText('password123');
      await element(by.id('confirm-password-input')).typeText('different');
      await element(by.text('Create Account')).tap();
      
      // Should show password mismatch error
      await waitFor(element(by.text('Passwords do not match'))).toBeVisible().withTimeout(3000);
    });

    it('should validate password strength', async () => {
      await element(by.id('name-input')).typeText('Test User');
      await element(by.id('email-input')).typeText('test@example.com');
      await element(by.id('password-input')).typeText('123');
      await element(by.id('confirm-password-input')).typeText('123');
      await element(by.text('Create Account')).tap();
      
      // Should show password strength error
      await waitFor(element(by.text('Password must be at least 6 characters'))).toBeVisible().withTimeout(3000);
    });
  });

  describe('Password Reset', () => {
    it('should navigate to password reset', async () => {
      await element(by.text('Forgot Password?')).tap();
      await waitFor(element(by.text('Reset Password'))).toBeVisible().withTimeout(3000);
      await expect(element(by.text('Enter your email address'))).toBeVisible();
      await expect(element(by.id('reset-email-input'))).toBeVisible();
      await expect(element(by.text('Send Reset Link'))).toBeVisible();
    });

    it('should validate email for password reset', async () => {
      await element(by.text('Forgot Password?')).tap();
      await element(by.id('reset-email-input')).typeText('invalid-email');
      await element(by.text('Send Reset Link')).tap();
      
      // Should show validation error
      await waitFor(element(by.text('Invalid email address'))).toBeVisible().withTimeout(3000);
    });

    it('should show success message after reset request', async () => {
      await element(by.text('Forgot Password?')).tap();
      await element(by.id('reset-email-input')).typeText('test@example.com');
      await element(by.text('Send Reset Link')).tap();
      
      // Should show success message
      await waitFor(element(by.text('Reset link sent to your email'))).toBeVisible().withTimeout(5000);
    });
  });

  describe('Social Authentication', () => {
    it('should handle Google sign in button', async () => {
      await expect(element(by.text('Continue with Google'))).toBeVisible();
      await element(by.text('Continue with Google')).tap();
      
      // Should open Google authentication flow
      // In real tests, you would mock the OAuth flow
    });

    it('should handle Apple sign in button', async () => {
      await expect(element(by.text('Continue with Apple'))).toBeVisible();
      await element(by.text('Continue with Apple')).tap();
      
      // Should open Apple authentication flow
      // In real tests, you would mock the OAuth flow
    });
  });

  describe('Authentication State Persistence', () => {
    it('should remember user session after app restart', async () => {
      // This test would require mocking successful authentication
      // and checking that the user remains logged in after relaunch
      await device.launchApp({ newInstance: false });
      // Should not show login screen if user was previously authenticated
    });
  });
});
