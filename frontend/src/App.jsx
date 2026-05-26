import { useEffect, useMemo, useState } from 'react'
import { createConversation, listConversations, listMessages, sendMessageStream } from './api'

function App() {
  const [conversations, setConversations] = useState([])
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('openai')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedConversationId) || null,
    [conversations, selectedConversationId],
  )

  async function refreshConversations() {
    const data = await listConversations()
    setConversations(data)
    if (!selectedConversationId && data.length > 0) {
      setSelectedConversationId(data[0].id)
    }
  }

  useEffect(() => {
    refreshConversations().catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!selectedConversationId) {
      setMessages([])
      return
    }
    listMessages(selectedConversationId)
      .then(setMessages)
      .catch((err) => setError(err.message))
  }, [selectedConversationId])

  async function handleCreateConversation() {
    setError('')
    try {
      const conversation = await createConversation()
      setConversations((previous) => [conversation, ...previous])
      setSelectedConversationId(conversation.id)
      setMessages([])
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSendMessage(event) {
    event.preventDefault()
    if (!selectedConversationId || !newMessage.trim() || loading) {
      return
    }

    const content = newMessage.trim()
    const tempUserId = `temp-user-${Date.now()}`
    const tempAssistantId = `temp-assistant-${Date.now()}`
    const optimisticUserMessage = {
      id: tempUserId,
      conversation_id: selectedConversationId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    const optimisticAssistantMessage = {
      id: tempAssistantId,
      conversation_id: selectedConversationId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }

    setLoading(true)
    setError('')
    setNewMessage('')
    setMessages((previous) => [...previous, optimisticUserMessage, optimisticAssistantMessage])

    try {
      await sendMessageStream(selectedConversationId, content, {
        provider: selectedProvider,
        onToken: (data) => {
          const text = data?.text || ''
          if (!text) {
            return
          }
          setMessages((previous) =>
            previous.map((message) =>
              message.id === tempAssistantId
                ? { ...message, content: `${message.content}${text}` }
                : message,
            ),
          )
        },
        onDone: (data) => {
          const streamedUser = data?.user_message
          const streamedAssistant = data?.assistant_message
          if (!streamedUser || !streamedAssistant) {
            return
          }
          setMessages((previous) =>
            previous.map((message) => {
              if (message.id === tempUserId) {
                return streamedUser
              }
              if (message.id === tempAssistantId) {
                return streamedAssistant
              }
              return message
            }),
          )
        },
        onError: (data) => {
          setError(data?.detail || 'Streaming failed')
        },
      })
      await refreshConversations()
    } catch (err) {
      setError(err.message)
      setMessages((previous) =>
        previous.filter((message) => message.id !== tempUserId && message.id !== tempAssistantId),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen p-4">
      <div className="mx-auto flex h-full max-w-6xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <aside className="w-72 border-r border-slate-200 p-4">
          <button
            type="button"
            onClick={handleCreateConversation}
            className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            New Conversation
          </button>
          <div className="mt-4 space-y-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => setSelectedConversationId(conversation.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                  conversation.id === selectedConversationId
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {conversation.title || 'Untitled Conversation'}
              </button>
            ))}
          </div>
        </aside>

        <main className="flex flex-1 flex-col">
          <header className="border-b border-slate-200 px-6 py-4">
            <h1 className="text-lg font-semibold text-slate-900">
              {selectedConversation?.title || 'Simple Chatbot'}
            </h1>
          </header>

          <section className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
                  message.role === 'user'
                    ? 'ml-auto bg-slate-900 text-white'
                    : 'bg-white text-slate-800 shadow-sm'
                }`}
              >
                {message.content}
              </div>
            ))}
            {messages.length === 0 && (
              <p className="text-sm text-slate-500">Create a conversation and send your first message.</p>
            )}
          </section>

          <form onSubmit={handleSendMessage} className="border-t border-slate-200 bg-white p-4">
            {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <select
                value={selectedProvider}
                onChange={(event) => setSelectedProvider(event.target.value)}
                disabled={loading}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
              <input
                type="text"
                value={newMessage}
                onChange={(event) => setNewMessage(event.target.value)}
                placeholder={selectedConversationId ? 'Type a message...' : 'Create a conversation first'}
                disabled={!selectedConversationId || loading}
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={!selectedConversationId || loading || !newMessage.trim()}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </form>
        </main>
      </div>
    </div>
  )
}

export default App
