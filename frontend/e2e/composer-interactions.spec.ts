import { test, expect } from '@playwright/test'
import { setupMockApi } from './fixtures/mockApi'

test.describe('Composer Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page, [])
    await page.goto('/')
  })

  test('handles multiline text with Shift+Enter without sending', async ({ page }) => {
    const input = page.getByLabel('Message input')
    const sendBtn = page.getByRole('button', { name: /send/i })

    await input.focus()
    await page.keyboard.type('First Line')
    await page.keyboard.down('Shift')
    await page.keyboard.press('Enter')
    await page.keyboard.up('Shift')
    await page.keyboard.type('Second Line')

    await expect(input).toHaveValue('First Line\nSecond Line')
    // Should NOT have sent the message yet
    await expect(page.getByTestId('message-user')).not.toBeVisible()
    await expect(sendBtn).toBeEnabled()
  })

  test('disables send button when text is empty or only whitespace', async ({ page }) => {
    const input = page.getByLabel('Message input')
    const sendBtn = page.getByRole('button', { name: /send/i })

    await expect(sendBtn).toBeDisabled()

    await input.fill('     ')
    await expect(sendBtn).toBeDisabled()

    await input.press('Enter')
    await expect(page.getByTestId('message-user')).not.toBeVisible()
  })

  test('clears input and disables composer during active stream', async ({ page }) => {
    const input = page.getByLabel('Message input')
    const sendBtn = page.getByRole('button', { name: /send/i })

    await input.fill('Start streaming test')
    await input.press('Enter')

    // Input should be immediately cleared
    await expect(input).toHaveValue('')

    // Wait for assistant reply to complete
    await expect(page.getByTestId('message-assistant')).toBeVisible()
    await expect(sendBtn).toBeDisabled() // disabled because input is now empty
  })
})
