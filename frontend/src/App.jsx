import { useEffect, useMemo, useState } from 'react'
import {
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  renameConversation,
  sendMessageStream,
} from './api'

function App() {
  const [conversations, setConversations] = useState([])
  const [selectedConversationId, setSelectedConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('openai')
  const [loading, setLoading] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [renameInput, setRenameInput] = useState('')
  const [renamingSaving, setRenamingSaving] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState(null)
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

  function handleSelectConversation(conversationId) {
    if (renaming) {
      setRenaming(false)
      setRenameInput('')
    }
    setSelectedConversationId(conversationId)
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

  function handleStartRename() {
    if (!selectedConversation) {
      return
    }
    setError('')
    setRenameInput(selectedConversation.title || '')
    setRenaming(true)
  }

  function handleCancelRename() {
    setRenaming(false)
    setRenameInput('')
  }

  async function handleSaveRename() {
    if (!selectedConversationId || renamingSaving) {
      return
    }

    setRenamingSaving(true)
    try {
      const updated = await renameConversation(selectedConversationId, renameInput)
      setConversations((previous) =>
        previous.map((conversation) =>
          conversation.id === updated.id ? updated : conversation,
        ),
      )
      setRenaming(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setRenamingSaving(false)
    }
  }

  async function handleDeleteConversation(conversationId) {
    if (!conversationId || deletingConversationId) {
      return
    }

    setError('')
    setDeletingConversationId(conversationId)
    try {
      await deleteConversation(conversationId)
      const remainingConversations = conversations.filter(
        (conversation) => conversation.id !== conversationId,
      )
      setConversations(remainingConversations)

      if (selectedConversationId === conversationId) {
        setRenaming(false)
        setRenameInput('')
        if (remainingConversations.length > 0) {
          setSelectedConversationId(remainingConversations[0].id)
        } else {
          setSelectedConversationId(null)
          setMessages([])
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingConversationId(null)
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
            {conversations.map((conversation) => {
              const isSelected = conversation.id === selectedConversationId
              const isEditingThis = isSelected && renaming
              return (
                <div
                  key={conversation.id}
                  className={`flex items-center gap-2 rounded-md px-2 py-1 ${
                    isSelected ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {isEditingThis ? (
                    <input
                      type="text"
                      value={renameInput}
                      onChange={(event) => setRenameInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault()
                          handleSaveRename()
                        } else if (event.key === 'Escape') {
                          event.preventDefault()
                          handleCancelRename()
                        }
                      }}
                      onBlur={handleSaveRename}
                      autoFocus
                      disabled={renamingSaving}
                      className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleSelectConversation(conversation.id)}
                      className={`w-full rounded-md px-1 py-1 text-left text-sm ${
                        isSelected ? 'text-white' : 'text-slate-700 hover:text-slate-900'
                      }`}
                    >
                      {conversation.title || 'Untitled Conversation'}
                    </button>
                  )}
                  {isSelected && (
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={(event) => {
                          event.stopPropagation()
                          if (isEditingThis) {
                            handleSaveRename()
                          } else {
                            handleStartRename()
                          }
                        }}
                        disabled={loading || renamingSaving || deletingConversationId === conversation.id}
                        className={`rounded-md p-1 disabled:cursor-not-allowed disabled:opacity-60 ${
                          isSelected ? 'text-white hover:bg-slate-800' : 'text-slate-600 hover:bg-slate-200'
                        }`}
                        aria-label={isEditingThis ? 'Save conversation title' : 'Edit conversation title'}
                      >
                        {isEditingThis ? (
                          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                            <path
                              fillRule="evenodd"
                              d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.5 7.565a1 1 0 0 1-1.425.01L3.28 9.8a1 1 0 0 1 1.44-1.386l3.79 3.937 6.793-6.854a1 1 0 0 1 1.4-.207Z"
                              clipRule="evenodd"
                            />
                          </svg>
                        ) : (
                          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                            <path d="M13.586 3.586a2 2 0 0 1 2.828 2.828l-8.12 8.12a2 2 0 0 1-.878.507l-2.58.737a.5.5 0 0 1-.618-.618l.737-2.58a2 2 0 0 1 .507-.878l8.124-8.116Z" />
                          </svg>
                        )}
                      </button>
                      <button
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={(event) => {
                          event.stopPropagation()
                          handleDeleteConversation(conversation.id)
                        }}
                        disabled={loading || renamingSaving || isEditingThis || deletingConversationId === conversation.id}
                        className={`rounded-md p-1 disabled:cursor-not-allowed disabled:opacity-60 ${
                          isSelected ? 'text-white hover:bg-slate-800' : 'text-slate-600 hover:bg-slate-200'
                        }`}
                        aria-label="Delete conversation"
                      >
                        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                          <path
                            fillRule="evenodd"
                            d="M8.5 2.5A1.5 1.5 0 0 0 7 4H5a1 1 0 1 0 0 2h.25l.66 8.58A2 2 0 0 0 7.9 16.5h4.2a2 2 0 0 0 1.99-1.92l.66-8.58H15a1 1 0 1 0 0-2h-2a1.5 1.5 0 0 0-1.5-1.5h-3Zm1.5 1.5h1a.5.5 0 0 1 .5.5H9.5a.5.5 0 0 1 .5-.5Zm-1 4a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-1.5 0v-4A.75.75 0 0 1 9 8Zm2.75.75a.75.75 0 0 0-1.5 0v4a.75.75 0 0 0 1.5 0v-4Z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
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
