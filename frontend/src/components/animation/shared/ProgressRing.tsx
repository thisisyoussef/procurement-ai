'use client'

import { useEffect } from 'react'
import { m, useSpring, useTransform } from 'motion/react'

interface ProgressRingProps {
  progress: number // 0-100
  size?: number
  strokeWidth?: number
  className?: string
}

export default function ProgressRing({
  progress,
  size = 40,
  strokeWidth = 3,
  className = '',
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius

  const spring = useSpring(0, { stiffness: 60, damping: 20 })
  const dashOffset = useTransform(spring, (v) => circumference * (1 - v / 100))

  useEffect(() => {
    spring.set(progress)
  }, [spring, progress])

  return (
    <svg width={size} height={size} className={className}>
      {/* Background track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-surface-3"
      />
      {/* Progress arc */}
      <m.circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        className="text-teal"
        style={{
          strokeDasharray: circumference,
          strokeDashoffset: dashOffset,
          rotate: '-90deg',
          transformOrigin: 'center',
        }}
      />
    </svg>
  )
}
