import { test, expect } from '@playwright/test';

test.describe('Agent Studio E2E', () => {
  test('should create a new agent and interact with it', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
    
    // Assume user is logged in via global setup or we mock it here.
    // For this test, we navigate to Agent Studio
    await page.click('text="Agent Studio"');
    
    // Click "Create Agent" button
    await page.click('button:has-text("Create Agent")');
    
    // Fill out the agent creation form
    await page.fill('input[name="name"]', 'Test E2E Agent');
    await page.fill('textarea[name="aiSystemPrompt"]', 'You are a test assistant.');
    
    // Submit form
    await page.click('button:has-text("Save")');
    
    // Verify agent is in the list
    await expect(page.locator('text="Test E2E Agent"')).toBeVisible();
    
    // Click on the agent to open chat
    await page.click('text="Test E2E Agent"');
    
    // Send a message
    await page.fill('input[placeholder="Type a message..."]', 'Hello');
    await page.click('button[aria-label="Send Message"]');
    
    // Wait for response (mocked or real depending on backend)
    // We just verify that a message bubble appears
    await expect(page.locator('.chat-message')).toHaveCount(2, { timeout: 10000 });
  });
});
