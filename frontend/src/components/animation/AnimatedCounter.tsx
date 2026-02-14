'use client'

import { useEffect, useRef } from 'react'
import { useSpring, useTransform, m } from 'motion/react'

interface AnimatedCounterProps {
  value: number
  className?: string
}

export default function AnimatedCounter({ value, className }: AnimatedCounterProps) {
  const spring = useSpring(0, { stiffness: 80, damping: 20, mass: 0.8 })
  const rounded = useTransform(spring, (v) => Math.round(v))
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    spring.set(value)
  }, [value, spring])

  useEffect(() => {
    const unsubscribe = rounded.on('change', (v) => {
      if (ref.current) ref.current.textContent = String(v)
    })
    return unsubscribe
  }, [rounded])

  return <span ref={ref} className={className}>{Math.round(value)}</span>
}
