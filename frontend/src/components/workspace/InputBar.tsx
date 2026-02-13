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
  const panelRef = useRef<HTMLDivElement>(null)

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

  // Auto-show history when messages arrive
  useEffect(() => {
    if (chat.messages.length > 0) setShowHistory(true)
  }, [chat.messages.length])

  // Scroll panel to bottom on new messages
  useEffect(() => {
    if (panelRef.current) {
      panelRef.current.scrollTop = panelRef.current.scrollHeight
    }
  }, [chat.messages, chat.streamingText])

  if (!projectId) {
    return (
      <div className="px-6 py-3 text-center border-t border-surface-3 bg-white">
        <span className="text-[11px] text-ink-4">
          Start a project to use the command bar
        </span>
      </div>
    )
  }

  return (
    <div className="border-t border-surface-3 bg-white shrink-0">
      {/* ── Chat History Slide-up ─────────────── */}
      {showHistory && (chat.messages.length > 0 || chat.streamingText) && (
        <div
          ref={panelRef}
          className="max-h-64 overflow-y-auto px-12 py-4 space-y-3 border-b border-surface-3 bg-cream/50"
        >
          {chat.messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-xl px-4 py-2.5 text-[12px] leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-teal text-white'
                    : 'bg-white card text-ink-2'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}

          {/* Streaming message */}
          {chat.streamingText && (
            <div className="flex justify-start">
              <div className="max-w-[70%] rounded-xl px-4 py-2.5 text-[12px] leading-relaxed bg-white card text-ink-2">
                <p className="whitespace-pre-wrap">{chat.streamingText}</p>
              </div>
            </div>
          )}

          {/* Action status */}
          {chat.actionStatus && (
            <div className="flex justify-center">
              <span className="text-[10px] px-3 py-1 bg-warm/10 text-warm rounded-full">
                {chat.actionStatus}
              </span>
            </div>
          )}

          <div ref={chat.messagesEndRef} />
        </div>
      )}

      {/* ── Quick Actions ─────────────────────── */}
      {chat.messages.length === 0 && !chat.isStreaming && (
        <div className="px-12 pt-3 flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => handleQuickAction(action)}
              className="text-[10px] px-3 py-1.5 rounded-full border border-surface-3 text-ink-4
                         hover:border-teal hover:text-teal transition-colors bg-white"
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {/* ── Input Row ─────────────────────────── */}
      <form onSubmit={handleSubmit} className="px-12 py-3">
        <div className="flex items-end gap-3">
          {/* Paperclip */}
          <button
            type="button"
            className="w-9 h-9 rounded-full border border-surface-3 flex items-center justify-center
                       text-ink-4 hover:text-teal hover:border-teal transition-colors shrink-0 mb-0.5"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={chat.input}
              onChange={(e) => chat.setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your project..."
              rows={1}
              disabled={chat.isStreaming}
              className="w-full resize-none rounded-xl border border-surface-3 bg-cream/50 px-4 py-2.5 text-[13px]
                         text-ink placeholder:text-ink-4
                         focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none
                         disabled:opacity-50 transition-all"
            />
            {chat.isStreaming && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[10px] text-teal">
                <span className="status-dot bg-teal animate-pulse-dot" />
                Thinking...
              </span>
            )}
          </div>

          {/* Send */}
          <button
            type="submit"
            disabled={!chat.input.trim() || chat.isStreaming}
            className="w-9 h-9 rounded-full bg-teal text-white flex items-center justify-center
                       hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed
                       transition-colors shrink-0 mb-0.5"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>

          {/* Toggle history */}
          {showHistory && chat.messages.length > 0 && (
            <button
              type="button"
              onClick={() => setShowHistory(false)}
              className="w-9 h-9 rounded-full border border-surface-3 flex items-center justify-center
                         text-ink-4 hover:text-ink-2 transition-colors shrink-0 mb-0.5"
              title="Hide chat"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
