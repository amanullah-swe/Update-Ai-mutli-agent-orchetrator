import { test, expect } from '@playwright/test'
import { setupMockApi } from './fixtures/mockApi'

test.describe('Accessibility & Keyboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page, [
      {
        id: 'chat-1',
        title: 'Accessibility Chat',
        created_at: '2026-09-28T10:00:00Z',
        updated_at: '2026-09-28T10:00:00Z',
        message_count: 0,
        last_message_at: null,
        messages: [],
      },
    ])
    await page.goto('/')
  })

  test('verifies key ARIA landmarks, roles, and accessible labels', async ({ page }) => {
    // 1. Sidebar landmark and title
    const sidebar = page.getByRole('complementary', { name: 'Conversations' })
    await expect(sidebar).toBeVisible()

    // 2. Conversation listbox and option roles
    const listbox = page.getByRole('listbox', { name: 'Conversation list' })
    await expect(listbox).toBeVisible()
    const option = page.getByRole('option')
    await expect(option).toBeVisible()

    // 3. Transcript messages region
    const transcript = page.getByLabel('Messages')
    await expect(transcript).toBeVisible()

    // 4. Composer input with label
    const composerInput = page.getByLabel('Message input')
    await expect(composerInput).toBeVisible()

    // 5. Send button
    const sendButton = page.getByRole('button', { name: 'Send' })
    await expect(sendButton).toBeVisible()
  })

  test('dismisses kebab action menu with Escape key', async ({ page }) => {
    const kebab = page.getByRole('button', { name: /more actions for accessibility chat/i })
    await kebab.click()

    // Menu should be open
    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Press Escape
    await page.keyboard.press('Escape')

    // Menu should close
    await expect(menu).not.toBeVisible()
  })
})
