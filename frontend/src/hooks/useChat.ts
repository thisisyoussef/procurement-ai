'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { authFetch } from '@/lib/auth'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface UseChatOptions {
  onResultsUpdated?: () => void
}

export function useChat(projectId: string | null, options?: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [actionStatus, setActionStatus] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming || !projectId) return

      const userMessage: ChatMessage = { role: 'user', content: text.trim() }
      setMessages((prev) => [...prev, userMessage])
      setInput('')
      setIsStreaming(true)
      setStreamingText('')
      setActionStatus(null)

      try {
        const response = await authFetch(
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
                setMessages((prev) => [
                  ...prev,
                  { role: 'assistant', content: accumulated },
                ])
                setStreamingText('')

                if (data.action && data.action.action_type !== 'none') {
                  setActionStatus(`Running: ${data.action.action_type}...`)
                }
              } else if (data.type === 'action_result') {
                setActionStatus(data.result)
                options?.onResultsUpdated?.()
                setTimeout(() => setActionStatus(null), 5000)
              } else if (data.type === 'error') {
                setMessages((prev) => [
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
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `Connection error: ${err.message}` },
        ])
      } finally {
        setIsStreaming(false)
        setStreamingText('')
      }
    },
    [projectId, isStreaming, options?.onResultsUpdated]
  )

  return {
    messages,
    input,
    setInput,
    isStreaming,
    streamingText,
    actionStatus,
    sendMessage,
    messagesEndRef,
  }
}
