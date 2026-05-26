function MessageComposer({
  error,
  handleSendMessage,
  loading,
  newMessage,
  selectedConversationId,
  selectedProvider,
  setNewMessage,
  setSelectedProvider,
}) {
  return (
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
  )
}

export default MessageComposer
