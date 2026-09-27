import { useCallback } from 'react'
import type { Message } from '../types/chat'
import { useChat } from '../hooks/useChat'
import { useConversations } from '../hooks/useConversations'
import { Sidebar } from '../components/Sidebar/Sidebar'
import { Transcript } from '../components/Transcript/Transcript'
import { Composer } from '../components/Composer/Composer'

/**
 * Chatbot home screen: sidebar (conversation list) · center transcript ·
 * bottom composer. Owns the wiring between conversation persistence and the
 * streaming chat hook.
 */
export function ChatPage() {
  const {
    conversations,
    activeId,
    createConversation,
    selectConversation,
    updateMessageList,
  } = useConversations()

  // Persist the working transcript into the conversation it is bound to.
  const persistTranscript = useCallback(
    (conversationId: string, nextMessages: Message[]) => {
      if (conversationId) updateMessageList(conversationId, nextMessages)
    },
    [updateMessageList],
  )

  const { messages, isLoading, error, send, load } = useChat({
    onTranscriptChange: persistTranscript,
  })

  const handleSelect = useCallback(
    (id: string) => {
      const target = conversations.find((c) => c.id === id)
      selectConversation(id)
      if (target) load(id, target.messages)
    },
    [conversations, load, selectConversation],
  )

  const handleNew = useCallback(() => {
    const id = createConversation().id
    selectConversation(id)
    load(id, [])
  }, [createConversation, load, selectConversation])

  const handleSend = useCallback(
    async (text: string) => {
      let conversationId = activeId
      if (!conversationId) {
        conversationId = createConversation().id
        selectConversation(conversationId)
      }
      await send(text, conversationId)
    },
    [activeId, createConversation, selectConversation, send],
  )

  return (
    <div className="chat-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
      />
      <main className="chat-layout__main">
        <Transcript messages={messages} isLoading={isLoading} />
        {error && (
          <p className="chat-layout__error" role="alert">
            {error}
          </p>
        )}
        <Composer onSend={handleSend} disabled={isLoading} />
      </main>
    </div>
  )
}