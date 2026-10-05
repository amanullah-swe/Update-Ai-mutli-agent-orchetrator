import { test, expect } from '@playwright/test'
import { setupMockApi } from './fixtures/mockApi'

test.describe('Error Recovery', () => {
  test('recovers from simulated stream failure and allows sending next message', async ({ page }) => {
    await setupMockApi(page, [])
    await page.goto('/')

    const input = page.getByLabel('Message input')

    // In MockChatService, messages containing "fail" or "error" stream an error event
    await input.fill('Trigger a failure please')
    await input.press('Enter')

    // Error message bubble should appear
    const errorBubble = page.locator('.message--error')
    await expect(errorBubble).toBeVisible()
    await expect(errorBubble).toContainText('simulated failure')

    // Composer input should be ready and enabled for next message
    await expect(input).toBeEnabled()
    await input.fill('Recovered message')
    await input.press('Enter')

    // Should now stream normal response
    await expect(page.getByText('Recovered message')).toBeVisible()
    await expect(page.getByTestId('message-assistant').last()).toContainText('canned, mock answer')
  })

  test('surfaces API network error alert when initial chats fail to load', async ({ page }) => {
    // Fail the GET /api/chats request
    await page.route('**/api/chats**', async (route) => {
      await route.abort('failed')
    })

    await page.goto('/')

    // Error alert banner should be visible
    const alert = page.getByRole('alert')
    await expect(alert).toBeVisible()
    await expect(alert).toContainText('Could not reach the backend')
  })
})
