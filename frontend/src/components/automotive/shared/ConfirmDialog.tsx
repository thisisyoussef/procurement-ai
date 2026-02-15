'use client'

import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  details?: string[]
  confirmLabel: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'default'
  onConfirm: () => void
  onCancel: () => void
}

const VARIANT_STYLES = {
  danger: 'bg-red-500 hover:bg-red-400 text-white',
  warning: 'bg-amber-500 hover:bg-amber-400 text-zinc-950',
  default: 'bg-amber-500 hover:bg-amber-400 text-zinc-950',
}

export default function ConfirmDialog({
  open,
  title,
  description,
  details,
  confirmLabel,
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (open) {
      // Focus the cancel button (safer default)
      confirmRef.current?.parentElement?.querySelector<HTMLButtonElement>('[data-cancel]')?.focus()
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onCancel])

  if (!open) return null

  const dialog = (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />
      {/* Dialog */}
      <div className="relative bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="p-6">
          {/* Icon */}
          {variant === 'danger' && (
            <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center mb-4">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 6v4m0 4h.01M18 10a8 8 0 11-16 0 8 8 0 0116 0z" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
          )}
          {variant === 'warning' && (
            <div className="w-10 h-10 rounded-full bg-amber-500/15 flex items-center justify-center mb-4">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 7v3m0 3h.01M3.5 17h13a1.5 1.5 0 001.3-2.25l-6.5-11a1.5 1.5 0 00-2.6 0l-6.5 11A1.5 1.5 0 003.5 17z" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
          )}

          <h3 className="text-lg font-semibold text-zinc-100 mb-2">{title}</h3>
          <p className="text-sm text-zinc-400 leading-relaxed">{description}</p>

          {/* Details list */}
          {details && details.length > 0 && (
            <div className="mt-4 bg-zinc-800/50 rounded-lg p-3 max-h-40 overflow-y-auto">
              {details.map((d, i) => (
                <p key={i} className="text-xs text-zinc-400 py-0.5">
                  {d}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 px-6 pb-6">
          <button
            data-cancel
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 text-sm font-medium bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            className={`flex-1 px-4 py-2.5 text-sm font-semibold rounded-lg transition-colors ${VARIANT_STYLES[variant]}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )

  if (typeof document !== 'undefined') {
    return createPortal(dialog, document.body)
  }
  return dialog
}
