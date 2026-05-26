function MessageList({ messages }) {
  return (
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
  )
}

export default MessageList
