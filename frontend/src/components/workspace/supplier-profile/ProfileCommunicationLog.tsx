'use client'

import type { SupplierProfileCommMessage } from '@/types/supplierProfile'

interface Props {
  messages: SupplierProfileCommMessage[]
}

export default function ProfileCommunicationLog({ messages }: Props) {
  return (
    <div className="flex flex-col">
      {messages.map((msg) => (
        <div
          key={msg.message_key}
          className="grid grid-cols-[80px_1fr] gap-4 py-4 border-b border-black/[.06] last:border-b-0 hover:bg-black/[.01] -mx-3 px-3 rounded-lg transition-colors"
        >
          <div className="text-[11px] text-ink-4 pt-0.5">
            {formatTimestamp(msg.created_at)}
          </div>
          <div>
            <div className="text-[13px] font-medium text-ink-2 mb-0.5">
              {msg.subject || (msg.direction === 'outbound' ? 'Message sent' : 'Response received')}
            </div>
            {msg.body_preview && (
              <div className="text-[12px] text-ink-3 leading-relaxed line-clamp-2">
                {msg.body_preview}
              </div>
            )}
            <div className="flex items-center gap-2 mt-1.5">
              <TypeBadge direction={msg.direction} channel={msg.channel} />
              <DeliveryDot status={msg.delivery_status} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function TypeBadge({ direction, channel }: { direction: string; channel: string }) {
  const label = direction === 'outbound'
    ? `${capitalize(channel)} sent`
    : direction === 'inbound'
      ? `${capitalize(channel)} received`
      : 'System'

  return (
    <span className="inline-block text-[9.5px] font-semibold text-ink-4 px-2 py-0.5 bg-black/[.03] rounded-full">
      {label}
    </span>
  )
}

function DeliveryDot({ status }: { status: string }) {
  if (!status || status === 'unknown') return null

  const colors: Record<string, string> = {
    sent: 'bg-teal/50',
    delivered: 'bg-teal',
    opened: 'bg-teal',
    clicked: 'bg-teal',
    bounced: 'bg-red-400',
    failed: 'bg-red-400',
  }
  const color = colors[status] || 'bg-ink-4/40'

  return (
    <span className="flex items-center gap-1 text-[9px] text-ink-4">
      <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
      {capitalize(status)}
    </span>
  )
}

function formatTimestamp(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()

  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })

  if (isToday) return `Today, ${time}`

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `Yesterday, ${time}`

  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + `, ${time}`
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
