'use client'

import { useEffect, useRef } from 'react'

/**
 * GSAP ScrollTrigger hook — dynamically imports GSAP only on the landing page.
 * Call this in useEffect to set up scroll-triggered animations.
 */
export function useScrollTimeline(
  setup: (gsap: typeof import('gsap').gsap, ScrollTrigger: typeof import('gsap/ScrollTrigger').ScrollTrigger) => (() => void) | void,
  deps: React.DependencyList = []
) {
  const cleanupRef = useRef<(() => void) | void>(undefined)

  useEffect(() => {
    let canceled = false

    const init = async () => {
      const [{ gsap }, { ScrollTrigger }] = await Promise.all([
        import('gsap'),
        import('gsap/ScrollTrigger'),
      ])
      gsap.registerPlugin(ScrollTrigger)

      if (canceled) return
      cleanupRef.current = setup(gsap, ScrollTrigger)
    }

    init()

    return () => {
      canceled = true
      if (typeof cleanupRef.current === 'function') {
        cleanupRef.current()
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
