'use client'

import { m, AnimatePresence } from 'motion/react'
import type { HTMLMotionProps } from 'motion/react'
import { fadeUp, fadeIn, scaleIn, staggerContainer, cardEntrance, slideInLeft } from './variants'
import { useReducedMotion } from './useReducedMotion'

type DivMotionProps = HTMLMotionProps<'div'> & { children: React.ReactNode }

export function FadeUp({ children, className, ...props }: DivMotionProps) {
  const reduced = useReducedMotion()
  if (reduced) return <div className={className}>{children}</div>
  return (
    <m.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-40px' }}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  )
}

export function FadeIn({ children, className, ...props }: DivMotionProps) {
  const reduced = useReducedMotion()
  if (reduced) return <div className={className}>{children}</div>
  return (
    <m.div
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className={className}
      {...props}
    >
      {children}
    </m.div>
  )
}

export function ScaleReveal({ children, className, ...props }: DivMotionProps) {
  const reduced = useReducedMotion()
  if (reduced) return <div className={className}>{children}</div>
  return (
    <m.div
      variants={scaleIn}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  )
}

export function SlideInLeft({ children, className, ...props }: DivMotionProps) {
  const reduced = useReducedMotion()
  if (reduced) return <div className={className}>{children}</div>
  return (
    <m.div
      variants={slideInLeft}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  )
}

export function StaggerList({ children, className, ...props }: DivMotionProps) {
  const reduced = useReducedMotion()
  if (reduced) return <div className={className}>{children}</div>
  return (
    <m.div
      variants={staggerContainer}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-20px' }}
      className={className}
      {...props}
    >
      {children}
    </m.div>
  )
}

export function StaggerItem({ children, className, ...props }: DivMotionProps) {
  return (
    <m.div variants={cardEntrance} className={className} {...props}>
      {children}
    </m.div>
  )
}

export function PresenceGroup({
  children,
  mode = 'wait',
}: {
  children: React.ReactNode
  mode?: 'wait' | 'sync' | 'popLayout'
}) {
  return <AnimatePresence mode={mode}>{children}</AnimatePresence>
}

export { m, AnimatePresence }
