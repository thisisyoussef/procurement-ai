import { DURATION, EASE_OUT_EXPO, STAGGER } from './config'
import type { Variants } from 'motion/react'

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.slow, ease: EASE_OUT_EXPO },
  },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: DURATION.normal },
  },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
}

export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -24 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
}

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 24 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
}

export const cardEntrance: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
}

export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: STAGGER.normal, delayChildren: 0.1 },
  },
}

export const staggerContainerFast: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: STAGGER.fast, delayChildren: 0.05 },
  },
}

export const expandCollapse: Variants = {
  hidden: { height: 0, opacity: 0 },
  visible: {
    height: 'auto',
    opacity: 1,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
  exit: {
    height: 0,
    opacity: 0,
    transition: { duration: DURATION.fast, ease: EASE_OUT_EXPO },
  },
}

export const phaseTransition: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE_OUT_EXPO },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.fast },
  },
}

export const toastSlide: Variants = {
  initial: { opacity: 0, y: -40, scale: 0.95 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 400, damping: 28 },
  },
  exit: {
    opacity: 0,
    y: -20,
    scale: 0.95,
    transition: { duration: DURATION.fast },
  },
}
