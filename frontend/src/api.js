const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Request failed')
  }
  return response.json()
}

export function createConversation(title) {
  return request('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title: title || null }),
  })
}

export function listConversations() {
  return request('/conversations')
}

export function listMessages(conversationId) {
  return request(`/conversations/${conversationId}/messages`)
}

export function sendMessage(conversationId, content) {
  return request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}
