import type { Metadata } from 'next'
import { DM_Serif_Text, Manrope } from 'next/font/google'
import RouteTrace from '@/components/RouteTrace'
import { LazyMotionProvider } from '@/lib/motion'
import './globals.css'

const dmSerif = DM_Serif_Text({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-heading',
  display: 'swap',
})

const manrope = Manrope({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Tamkin — Tell us what you need made',
  description: 'Find the right people to make your stuff. Manage them like a pro.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${dmSerif.variable} ${manrope.variable} font-body antialiased`}>
        <LazyMotionProvider>
          <RouteTrace />
          {children}
        </LazyMotionProvider>
      </body>
    </html>
  )
}
