import { test, expect } from '@playwright/test'
import { setupMockApi } from './fixtures/mockApi'

test.describe('Chat Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page, [])
    await page.goto('/')
  })

  test('displays initial welcome state and sends first message with auto-titling and streaming response', async ({
    page,
  }) => {
    // 1. Verify initial empty welcome screen
    await expect(page.getByText('Ask anything about your documents.')).toBeVisible()
    await expect(page.getByText('No conversations yet — start a new one.')).toBeVisible()

    // 2. Type message into composer
    const input = page.getByLabel('Message input')
    await expect(input).toBeVisible()
    await input.fill('What is hybrid retrieval?')

    // 3. Send message
    await input.press('Enter')

    // 4. Verify user message appears in transcript
    const userMessage = page.getByTestId('message-user')
    await expect(userMessage).toBeVisible()
    await expect(userMessage).toContainText('What is hybrid retrieval?')

    // 5. Verify assistant response streams in
    const assistantMessage = page.getByTestId('message-assistant')
    await expect(assistantMessage).toBeVisible()
    await expect(assistantMessage).toContainText('canned, mock answer')
    await expect(assistantMessage.getByRole('listitem').first()).toBeVisible()

    // 6. Verify sources section rendered
    const sources = assistantMessage.getByTestId('sources')
    await expect(sources).toBeVisible()
    await expect(sources).toContainText('doc_spec_001')

    // 7. Verify sidebar conversation item was auto-titled
    const sidebarItem = page.getByRole('option')
    await expect(sidebarItem).toBeVisible()
    await expect(sidebarItem).toContainText('What is hybrid retrieval?')
  })
})
