import { useEffect, useMemo, useState } from 'react'
import {
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  renameConversation,
  sendMessageStream,
} from '../api'

function useChatApp() {
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

  return {
    conversations,
    deletingConversationId,
    error,
    handleCancelRename,
    handleCreateConversation,
    handleDeleteConversation,
    handleSaveRename,
    handleSelectConversation,
    handleSendMessage,
    handleStartRename,
    loading,
    messages,
    newMessage,
    renameInput,
    renaming,
    renamingSaving,
    selectedConversation,
    selectedConversationId,
    selectedProvider,
    setNewMessage,
    setRenameInput,
    setSelectedProvider,
  }
}

export default useChatApp
