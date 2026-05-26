function ConversationSidebar({
  conversations,
  deletingConversationId,
  handleCancelRename,
  handleCreateConversation,
  handleDeleteConversation,
  handleSaveRename,
  handleSelectConversation,
  handleStartRename,
  loading,
  renameInput,
  renaming,
  renamingSaving,
  selectedConversationId,
  setRenameInput,
}) {
  return (
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
  )
}

export default ConversationSidebar
