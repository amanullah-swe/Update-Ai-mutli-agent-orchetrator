import { test, expect } from '@playwright/test'
import { setupMockApi, type MockChat } from './fixtures/mockApi'

test.describe('Conversations CRUD', () => {
  const initialChats: MockChat[] = [
    {
      id: 'chat-alpha',
      title: 'Alpha Discussion',
      created_at: '2026-09-28T10:00:00Z',
      updated_at: '2026-09-28T10:00:00Z',
      message_count: 2,
      last_message_at: '2026-09-28T10:00:00Z',
      messages: [
        { id: 'm1', role: 'user', content: 'Alpha user question', created_at: '2026-09-28T10:00:00Z' },
        { id: 'm2', role: 'assistant', content: 'Alpha assistant response', created_at: '2026-09-28T10:00:01Z' },
      ],
    },
    {
      id: 'chat-beta',
      title: 'Beta Discussion',
      created_at: '2026-09-28T11:00:00Z',
      updated_at: '2026-09-28T11:00:00Z',
      message_count: 2,
      last_message_at: '2026-09-28T11:00:00Z',
      messages: [
        { id: 'm3', role: 'user', content: 'Beta user question', created_at: '2026-09-28T11:00:00Z' },
        { id: 'm4', role: 'assistant', content: 'Beta assistant response', created_at: '2026-09-28T11:00:01Z' },
      ],
    },
  ]

  test.beforeEach(async ({ page }) => {
    await setupMockApi(page, initialChats)
    await page.goto('/')
  })

  test('lists existing conversations and switches between them', async ({ page }) => {
    await expect(page.getByText('Alpha Discussion')).toBeVisible()
    await expect(page.getByText('Beta Discussion')).toBeVisible()

    // Select Alpha
    await page.getByText('Alpha Discussion').click()
    const messagesRegion = page.getByLabel('Messages')
    await expect(messagesRegion.getByText('Alpha user question')).toBeVisible()
    await expect(messagesRegion.getByText('Alpha assistant response')).toBeVisible()

    // Select Beta
    await page.getByText('Beta Discussion').click()
    await expect(messagesRegion.getByText('Beta user question')).toBeVisible()
    await expect(messagesRegion.getByText('Beta assistant response')).toBeVisible()
  })

  test('creates a new conversation using "+ New" button', async ({ page }) => {
    await page.getByRole('button', { name: /new conversation/i }).click()

    // An untitled chat should appear in sidebar
    await expect(page.getByText('Untitled chat')).toBeVisible()
    // Transcript should be cleared to empty state
    await expect(page.getByText('Ask anything about your documents.')).toBeVisible()
  })

  test('renames conversation inline via kebab menu', async ({ page }) => {
    // Open kebab menu for Alpha Discussion
    const kebab = page.getByRole('button', { name: /more actions for alpha discussion/i })
    await kebab.click()

    // Click Rename
    await page.getByRole('menuitem', { name: /rename/i }).click()

    // Input should be active
    const renameInput = page.getByLabel('Rename conversation')
    await expect(renameInput).toBeVisible()
    await renameInput.fill('Updated Project Roadmap')
    await renameInput.press('Enter')

    // Verify title updated
    await expect(page.getByText('Updated Project Roadmap')).toBeVisible()
    await expect(page.getByText('Alpha Discussion')).not.toBeVisible()
  })

  test('deletes conversation with confirmation dialog', async ({ page }) => {
    // Select Beta to make it active
    await page.getByText('Beta Discussion').click()
    await expect(page.getByText('Beta user question')).toBeVisible()

    // Open kebab menu and click Delete
    const kebab = page.getByRole('button', { name: /more actions for beta discussion/i })
    await kebab.click()
    await page.getByRole('menuitem', { name: /^delete$/i }).click()

    // Verify confirmation modal
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('Delete conversation?')

    // Test Cancel first
    await dialog.getByRole('button', { name: /cancel/i }).click()
    await expect(dialog).not.toBeVisible()
    await expect(page.getByText('Beta Discussion')).toBeVisible()

    // Open again and confirm
    await kebab.click()
    await page.getByRole('menuitem', { name: /^delete$/i }).click()
    await dialog.getByRole('button', { name: /^delete$/i }).click()

    // Verify chat removed and transcript reset
    await expect(page.getByText('Beta Discussion')).not.toBeVisible()
    await expect(page.getByText('Ask anything about your documents.')).toBeVisible()
  })
})
