'use client'

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, m } from '@/lib/motion'
import { useWorkspace } from '@/contexts/WorkspaceContext'

/* ────────────────────────────────────────────────────────
 * StageTransitionToast — brief announcement when the
 * pipeline moves to a new stage.
 *
 * Shows for 3 seconds then auto-dismisses.
 * ──────────────────────────────────────────────────────── */

const TRANSITION_MESSAGES: Record<string, string> = {
  parsing: 'Understanding your brief...',
  discovering: 'Brief understood. Starting supplier search...',
  verifying: 'Found suppliers. Now checking their credibility...',
  comparing: 'Verification complete. Building your comparison...',
  recommending: 'Comparison ready. Preparing my recommendation...',
  complete: 'All done. Here are my picks.',
  outreaching: 'Sending outreach on your behalf...',
}

export default function StageTransitionToast() {
  const { status } = useWorkspace()
  const [visible, setVisible] = useState(false)
  const [message, setMessage] = useState('')
  const prevStageRef = useRef<string | null>(null)

  const currentStage = status?.current_stage || null

  useEffect(() => {
    if (!currentStage) return
    if (prevStageRef.current === currentStage) return
    if (prevStageRef.current === null) {
      // First load — don't show toast
      prevStageRef.current = currentStage
      return
    }

    prevStageRef.current = currentStage
    const msg = TRANSITION_MESSAGES[currentStage]
    if (!msg) return

    setMessage(msg)
    setVisible(true)

    const timer = setTimeout(() => setVisible(false), 3000)
    return () => clearTimeout(timer)
  }, [currentStage])

  return (
    <AnimatePresence>
      {visible && (
        <m.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50
                     bg-ink text-white text-[12px] px-4 py-2.5 rounded-full shadow-lg"
        >
          {message}
        </m.div>
      )}
    </AnimatePresence>
  )
}
