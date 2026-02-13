'use client'

import { useState, useRef, useEffect } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import { useChat } from '@/hooks/useChat'

const QUICK_ACTIONS = [
  'Why this ranking?',
  'Prioritize speed over price',
  'Show me budget options',
  'Draft outreach emails for top 3',
]

export default function InputBar() {
  const { projectId, refreshStatus } = useWorkspace()
  const chat = useChat(projectId, { onResultsUpdated: refreshStatus })
  const [showHistory, setShowHistory] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (chat.input.trim()) {
      chat.sendMessage(chat.input)
      setShowHistory(true)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (chat.input.trim()) {
        chat.sendMessage(chat.input)
        setShowHistory(true)
      }
    }
  }

  const handleQuickAction = (action: string) => {
    chat.sendMessage(action)
    setShowHistory(true)
  }

  // Show history when there are messages
  useEffect(() => {
    if (chat.messages.length > 0) setShowHistory(true)
  }, [chat.messages.length])

  if (!projectId) {
    return (
      <div className="px-6 py-3 text-center">
        <span className="text-xs text-workspace-muted/50">
          Start a project to use the command bar
        </span>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto w-full">
      {/* ── Message History Panel ───────────────────── */}
      {showHistory && (chat.messages.length > 0 || chat.streamingText) && (
        <div className="max-h-72 overflow-y-auto px-6 py-3 space-y-3 border-b border-workspace-border/50">
          {chat.messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-teal/20 text-teal-100'
                    : 'bg-workspace-hover text-workspace-text'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}

          {/* Streaming message */}
          {chat.streamingText && (
            <div className="flex justify-start">
              <div className="max-w-[75%] rounded-lg px-3 py-2 text-sm bg-workspace-hover text-workspace-text">
                <p className="whitespace-pre-wrap">{chat.streamingText}</p>
                <span className="inline-block w-1.5 h-4 bg-teal animate-pulse ml-0.5 align-text-bottom" />
              </div>
            </div>
          )}

          {/* Action status */}
          {chat.actionStatus && (
            <div className="flex justify-center">
              <span className="text-[10px] px-3 py-1 bg-gold/10 border border-gold/20 text-gold rounded-full">
                {chat.actionStatus}
              </span>
            </div>
          )}

          <div ref={chat.messagesEndRef} />
        </div>
      )}

      {/* ── Quick Actions ──────────────────────────── */}
      {chat.messages.length === 0 && !chat.isStreaming && (
        <div className="px-6 pt-2 flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => handleQuickAction(action)}
              className="text-[11px] px-3 py-1 bg-workspace-hover text-workspace-muted rounded-full
                         hover:bg-teal/10 hover:text-teal transition-colors border border-workspace-border"
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {/* ── Input ──────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="px-6 py-3">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={chat.input}
              onChange={(e) => chat.setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your project..."
              rows={1}
              disabled={chat.isStreaming}
              className="w-full resize-none rounded-xl bg-workspace-hover border border-workspace-border px-4 py-2.5 text-sm
                         text-workspace-text placeholder:text-workspace-muted/50
                         focus:ring-2 focus:ring-teal/30 focus:border-teal/50 focus:outline-none
                         disabled:opacity-50 transition-all"
            />
            {chat.isStreaming && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[10px] text-teal">
                <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
                Thinking...
              </span>
            )}
          </div>
          <button
            type="submit"
            disabled={!chat.input.trim() || chat.isStreaming}
            className="px-4 py-2.5 bg-teal text-workspace-bg rounded-xl text-sm font-medium
                       hover:bg-teal-400 disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors shrink-0"
          >
            Send
          </button>
          {showHistory && chat.messages.length > 0 && (
            <button
              type="button"
              onClick={() => setShowHistory(false)}
              className="px-2 py-2.5 text-workspace-muted hover:text-workspace-text text-xs transition-colors"
              title="Hide chat history"
            >
              ▼
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
