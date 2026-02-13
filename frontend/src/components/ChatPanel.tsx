'use client'

import { useState, useRef, useEffect } from 'react'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  projectId: string
  onResultsUpdated: () => void
}

const QUICK_ACTIONS = [
  'Why this ranking?',
  'Prioritize speed over price',
  'Show me budget options',
  'Draft outreach emails for top 3',
]

export default function ChatPanel({ projectId, onResultsUpdated }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [actionStatus, setActionStatus] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const sendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return

    const userMessage: ChatMessage = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)
    setStreamingText('')
    setActionStatus(null)

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim() }),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const data = JSON.parse(raw)

            if (data.type === 'token') {
              accumulated += data.content
              setStreamingText(accumulated)
            } else if (data.type === 'done') {
              // Finalize the assistant message
              setMessages(prev => [...prev, { role: 'assistant', content: accumulated }])
              setStreamingText('')

              if (data.action && data.action.action_type !== 'none') {
                setActionStatus(`Running: ${data.action.action_type}...`)
              }
            } else if (data.type === 'action_result') {
              setActionStatus(data.result)
              // Trigger a refresh so parent picks up updated data
              onResultsUpdated()
              setTimeout(() => setActionStatus(null), 5000)
            } else if (data.type === 'error') {
              setMessages(prev => [
                ...prev,
                { role: 'assistant', content: `Error: ${data.message}` },
              ])
            }
          } catch {
            // Skip malformed JSON lines
          }
        }
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Connection error: ${err.message}` },
      ])
    } finally {
      setIsStreaming(false)
      setStreamingText('')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <h2 className="text-base font-semibold text-slate-900">
            Ask follow-up questions
          </h2>
          {isStreaming && (
            <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-blue-600">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Thinking...
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="max-h-96 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && !streamingText && (
          <p className="text-sm text-slate-400 text-center py-4">
            Ask questions about the results, adjust preferences, or request actions.
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed bg-slate-100 text-slate-800">
              <p className="whitespace-pre-wrap">{streamingText}</p>
              <span className="inline-block w-1.5 h-4 bg-blue-500 animate-pulse ml-0.5 align-text-bottom" />
            </div>
          </div>
        )}

        {/* Action status */}
        {actionStatus && (
          <div className="flex justify-center">
            <span className="text-xs px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-700 rounded-full">
              {actionStatus}
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      {messages.length === 0 && !isStreaming && (
        <div className="px-6 pb-2 flex flex-wrap gap-2">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => sendMessage(action)}
              className="text-xs px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full
                         hover:bg-blue-100 transition-colors border border-blue-200"
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-6 py-3 border-t border-slate-200">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the results..."
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       disabled:opacity-50 text-slate-900 placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors shrink-0"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
