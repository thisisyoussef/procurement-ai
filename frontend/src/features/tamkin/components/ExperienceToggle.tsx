'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useTransition } from 'react'
import { Power } from 'lucide-react'

import { setTamkinExperienceCookie } from '@/lib/featureFlags'

interface ExperienceToggleProps {
  enabled: boolean
  placement?: 'fixed' | 'inline'
}

export default function ExperienceToggle({
  enabled,
  placement = 'fixed',
}: ExperienceToggleProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [isPending, startTransition] = useTransition()

  const handleToggle = () => {
    const nextEnabled = !enabled
    setTamkinExperienceCookie(nextEnabled)

    startTransition(() => {
      if (!nextEnabled && pathname.startsWith('/workspace/')) {
        router.push('/')
        return
      }
      router.refresh()
    })
  }

  const containerClass =
    placement === 'fixed'
      ? 'fixed bottom-4 right-4 z-[80]'
      : 'relative'

  return (
    <div className={containerClass}>
      <button
        type="button"
        onClick={handleToggle}
        disabled={isPending}
        aria-label="Toggle Tamkin testing experience"
        className={`group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium shadow-lg transition ${
          enabled
            ? 'border-emerald-300/60 bg-emerald-500/20 text-emerald-50 hover:bg-emerald-500/28'
            : 'border-slate-300/70 bg-white text-slate-700 hover:bg-slate-50'
        } ${isPending ? 'cursor-wait opacity-75' : ''}`}
      >
        <Power className="h-3.5 w-3.5" />
        <span>{enabled ? 'Tamkin ON' : 'Tamkin OFF'}</span>
      </button>
    </div>
  )
}
