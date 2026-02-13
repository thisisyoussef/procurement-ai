import type { Metadata } from 'next'
import './globals.css'

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
      <body className="antialiased">{children}</body>
    </html>
  )
}
