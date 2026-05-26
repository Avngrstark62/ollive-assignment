import ConversationSidebar from './components/ConversationSidebar'
import MessageComposer from './components/MessageComposer'
import MessageList from './components/MessageList'
import useChatApp from './hooks/useChatApp'

function App() {
  const {
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
  } = useChatApp()

  return (
    <div className="h-screen p-4">
      <div className="mx-auto flex h-full max-w-6xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <ConversationSidebar
          conversations={conversations}
          deletingConversationId={deletingConversationId}
          handleCancelRename={handleCancelRename}
          handleCreateConversation={handleCreateConversation}
          handleDeleteConversation={handleDeleteConversation}
          handleSaveRename={handleSaveRename}
          handleSelectConversation={handleSelectConversation}
          handleStartRename={handleStartRename}
          loading={loading}
          renameInput={renameInput}
          renaming={renaming}
          renamingSaving={renamingSaving}
          selectedConversationId={selectedConversationId}
          setRenameInput={setRenameInput}
        />

        <main className="flex flex-1 flex-col">
          <header className="border-b border-slate-200 px-6 py-4">
            <h1 className="text-lg font-semibold text-slate-900">
              {selectedConversation?.title || 'Simple Chatbot'}
            </h1>
          </header>

          <MessageList messages={messages} />

          <MessageComposer
            error={error}
            handleSendMessage={handleSendMessage}
            loading={loading}
            newMessage={newMessage}
            selectedConversationId={selectedConversationId}
            selectedProvider={selectedProvider}
            setNewMessage={setNewMessage}
            setSelectedProvider={setSelectedProvider}
          />
        </main>
      </div>
    </div>
  )
}

export default App
