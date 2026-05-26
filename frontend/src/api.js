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
  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    return null
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

export function renameConversation(conversationId, title) {
  return request(`/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title: title || null }),
  })
}

export function deleteConversation(conversationId) {
  return request(`/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}

export function sendMessage(conversationId, content, options = {}) {
  const payload = {
    content,
    ...(options.provider ? { provider: options.provider } : {}),
    ...(options.model ? { model: options.model } : {}),
  }
  return request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function sendMessageStream(conversationId, content, options = {}) {
  const payload = {
    content,
    ...(options.provider ? { provider: options.provider } : {}),
    ...(options.model ? { model: options.model } : {}),
  }
  const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Request failed')
  }

  if (!response.body) {
    throw new Error('Streaming is not supported by this browser.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let streamCompleted = false

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const rawEvent of events) {
      const parsed = parseSseEvent(rawEvent)
      if (!parsed) {
        continue
      }
      const { event, data } = parsed
      if (event === 'token') {
        options.onToken?.(data)
      } else if (event === 'done') {
        streamCompleted = true
        options.onDone?.(data)
      } else if (event === 'error') {
        options.onError?.(data)
        throw new Error(data?.detail || 'Streaming failed')
      }
    }
  }

  if (!streamCompleted) {
    throw new Error('Stream ended before completion')
  }
}

function parseSseEvent(rawEvent) {
  const lines = rawEvent.split('\n')
  let event = 'message'
  let dataString = ''

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataString += line.slice(5).trim()
    }
  }

  if (!dataString) {
    return null
  }

  let data
  try {
    data = JSON.parse(dataString)
  } catch {
    data = { detail: dataString }
  }

  return { event, data }
}
