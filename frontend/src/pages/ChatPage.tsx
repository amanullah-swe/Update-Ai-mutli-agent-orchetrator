import { useCallback, useState } from 'react'
import type { Message } from '../types/chat'
import { useChat } from '../hooks/useChat'
import { useConversations } from '../hooks/useConversations'
import { Sidebar } from '../components/Sidebar/Sidebar'
import { Transcript } from '../components/Transcript/Transcript'
import { Composer } from '../components/Composer/Composer'
import { ConfirmDialog } from '../components/ConfirmDialog/ConfirmDialog'
import { getChat } from '../services/chatApi'
import { conversationTitle } from '../utils/messages'

/**
 * Chatbot home screen: sidebar (conversation list) · center transcript ·
 * bottom composer. The backend is the source of truth — conversations come
 * from the chat CRUD API, the transcript is fetched on selection, and messages
 * stream over the WebSocket transport behind `useChat`.
 */
export function ChatPage() {
  const {
    conversations,
    activeId,
    loading: listLoading,
    error: listError,
    createConversation,
    selectConversation,
    updateMessageList,
    renameConversation,
    deleteConversation,
  } = useConversations()

  const [transcriptLoading, setTranscriptLoading] = useState(false)
  const [transcriptError, setTranscriptError] = useState<string | null>(null)
  // The chat awaiting delete confirmation — set by the sidebar's Delete menu
  // item, consumed (and cleared) by the ConfirmDialog. Null means "no modal".
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)

  // Keep the in-memory transcript (sidebar preview) for the conversation being
  // streamed into. The server already persists it — this is UI state only.
  const persistTranscript = useCallback(
    (conversationId: string, nextMessages: Message[]) => {
      if (conversationId) updateMessageList(conversationId, nextMessages)
    },
    [updateMessageList],
  )

  const { messages, isLoading, error: chatError, send, load } = useChat({
    onTranscriptChange: persistTranscript,
  })

  const handleSelect = useCallback(
    async (id: string) => {
      selectConversation(id)
      setTranscriptError(null)
      setTranscriptLoading(true)
      try {
        const detail = await getChat(id)
        load(id, detail.messages)
      } catch (err) {
        setTranscriptError(err instanceof Error ? err.message : String(err))
        load(id, [])
      } finally {
        setTranscriptLoading(false)
      }
    },
    [load, selectConversation],
  )

  const handleNew = useCallback(async () => {
    const conversation = await createConversation()
    if (!conversation) return
    load(conversation.id, [])
  }, [createConversation, load])

  // The sidebar's Delete menu item only reports *the user asked* — confirmation
  // happens here. Record the target and let ConfirmDialog ask.
  const handleDeleteRequest = useCallback(
    (id: string) => {
      const target = conversations.find((c) => c.id === id)
      setPendingDelete({ id, title: target?.title ?? 'Untitled chat' })
    },
    [conversations],
  )

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete) return
    const { id } = pendingDelete
    setPendingDelete(null)
    const deleted = await deleteConversation(id)
    // The active chat's transcript is local state; clear it when that chat
    // goes away so the pane returns to the empty state.
    if (deleted && activeId === id) load('', [])
  }, [activeId, deleteConversation, load, pendingDelete])

  const handleSend = useCallback(
    async (text: string) => {
      let conversationId = activeId
      if (!conversationId) {
        const created = await createConversation()
        if (!created) return
        conversationId = created.id
        selectConversation(conversationId)
      }

      // A chat with a null title and no local messages is brand-new; give it a
      // title derived from its first user message (the server has no
      // auto-titling — the client renames, per 007 spec).
      const startsUntitled = conversations.some(
        (c) => c.id === conversationId && c.title === null,
      )

      await send(text, conversationId)

      if (startsUntitled) {
        const title = conversationTitle(text.trim())
        void renameConversation(conversationId, title)
      }
    },
    [activeId, conversations, createConversation, renameConversation, selectConversation, send],
  )

  const pageError = listError ?? transcriptError ?? chatError

  return (
    <div className="chat-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
        onRename={renameConversation}
        onDelete={handleDeleteRequest}
      />
      <main className="chat-layout__main">
        <Transcript
          messages={messages}
          isLoading={isLoading}
          loading={transcriptLoading || (listLoading && activeId === null)}
        />
        {pageError && (
          <p className="chat-layout__error" role="alert">
            {pageError}
          </p>
        )}
        <Composer onSend={handleSend} disabled={isLoading} />
      </main>
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete conversation?"
        message={
          pendingDelete && (
            <>
              “
              <strong>{pendingDelete.title}</strong>
              ” and all of its messages will be permanently removed.
            </>
          )
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}