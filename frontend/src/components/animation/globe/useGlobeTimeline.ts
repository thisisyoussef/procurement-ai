'use client'

import { useEffect, useRef, useCallback } from 'react'

type GSAPInstance = typeof import('gsap').gsap

/**
 * Hook that dynamically imports GSAP and provides an `animateArc` function
 * to draw arcs via stroke-dashoffset animation.
 *
 * GSAP is only loaded when the discovery globe mounts — zero main bundle impact.
 */
export function useGlobeTimeline(svgRef: React.RefObject<SVGSVGElement | null>) {
  const gsapRef = useRef<GSAPInstance | null>(null)
  const tlRef = useRef<gsap.core.Timeline | null>(null)

  // Load GSAP on mount
  useEffect(() => {
    let cancelled = false

    async function loadGSAP() {
      try {
        const mod = await import('gsap')
        if (!cancelled) {
          gsapRef.current = mod.gsap
        }
      } catch {
        // GSAP not available — arcs just appear without animation
      }
    }

    loadGSAP()
    return () => {
      cancelled = true
      tlRef.current?.kill()
    }
  }, [])

  /**
   * Animate a specific arc path using stroke-dashoffset.
   * The path must have `data-region={regionLabel}` attribute.
   */
  const animateArc = useCallback(
    (regionLabel: string, options?: { duration?: number; onComplete?: () => void }) => {
      const gsap = gsapRef.current
      const svg = svgRef.current
      if (!gsap || !svg) return

      const selector = `.globe-arc-${regionLabel.replace(/\s/g, '-')}`
      const path = svg.querySelector<SVGPathElement>(selector)
      if (!path) return

      const length = path.getTotalLength()

      // Set initial state: fully hidden
      gsap.set(path, {
        strokeDasharray: length,
        strokeDashoffset: length,
        attr: { 'stroke-opacity': 0.8 },
      })

      // Animate: draw the arc from center to destination
      gsap.to(path, {
        strokeDashoffset: 0,
        duration: options?.duration ?? 0.6,
        ease: 'power2.out',
        onComplete: options?.onComplete,
      })
    },
    [svgRef],
  )

  /**
   * Pulse all dots (used for "searching supplier memory" events).
   * Briefly brightens all dots then fades back.
   */
  const pulseAllDots = useCallback(() => {
    const gsap = gsapRef.current
    const svg = svgRef.current
    if (!gsap || !svg) return

    const dots = svg.querySelectorAll('.globe-dots circle')
    gsap.to(dots, {
      attr: { opacity: 0.5 },
      duration: 0.3,
      ease: 'power1.in',
      stagger: { each: 0.002, from: 'center' },
      yoyo: true,
      repeat: 1,
    })
  }, [svgRef])

  /**
   * Final glow: all dots light up teal simultaneously.
   */
  const finalGlow = useCallback(() => {
    const gsap = gsapRef.current
    const svg = svgRef.current
    if (!gsap || !svg) return

    const dots = svg.querySelectorAll('.globe-dots circle')
    gsap.to(dots, {
      attr: { opacity: 0.7 },
      fill: 'var(--color-teal)',
      duration: 0.8,
      ease: 'power2.out',
      stagger: { each: 0.001, from: 'center' },
    })
  }, [svgRef])

  return { animateArc, pulseAllDots, finalGlow, gsapReady: gsapRef.current !== null }
}
