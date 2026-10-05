import type { Page } from '@playwright/test'

export interface MockChat {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
  last_message_at: string | null
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
  }>
}

/**
 * Sets up Playwright network route mocking for the chat CRUD API.
 * Allows E2E tests to run hermetically without needing a live backend database.
 */
export async function setupMockApi(page: Page, initialChats: MockChat[] = []) {
  const chats = new Map<string, MockChat>(initialChats.map((c) => [c.id, { ...c }]))

  await page.route('**/api/chats**', async (route) => {
    const request = route.request()
    const method = request.method()
    const url = new URL(request.url())
    const pathParts = url.pathname.split('/').filter(Boolean)
    // pathParts: ['api', 'chats'] or ['api', 'chats', '<id>']
    const chatId = pathParts.length > 2 ? pathParts[2] : null

    if (method === 'GET' && !chatId) {
      // listChats()
      const list = Array.from(chats.values()).map((c) => ({
        id: c.id,
        title: c.title,
        created_at: c.created_at,
        updated_at: c.updated_at,
        message_count: c.message_count,
        last_message_at: c.last_message_at,
      }))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: list, total: list.length }),
      })
      return
    }

    if (method === 'POST' && !chatId) {
      // createChat()
      const body = request.postDataJSON() || {}
      const id = `chat-${Date.now()}`
      const now = new Date().toISOString()
      const newChat: MockChat = {
        id,
        title: body.title || null,
        created_at: now,
        updated_at: now,
        message_count: 0,
        last_message_at: null,
        messages: [],
      }
      chats.set(id, newChat)
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newChat),
      })
      return
    }

    if (chatId) {
      const chat = chats.get(chatId)

      if (method === 'GET') {
        if (!chat) {
          await route.fulfill({ status: 404, body: JSON.stringify({ detail: { message: 'Chat not found' } }) })
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(chat),
        })
        return
      }

      if (method === 'PATCH') {
        if (!chat) {
          await route.fulfill({ status: 404, body: JSON.stringify({ detail: { message: 'Chat not found' } }) })
          return
        }
        const body = request.postDataJSON() || {}
        chat.title = body.title
        chat.updated_at = new Date().toISOString()
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(chat),
        })
        return
      }

      if (method === 'DELETE') {
        chats.delete(chatId)
        await route.fulfill({ status: 204 })
        return
      }
    }

    await route.continue()
  })

  return chats
}
