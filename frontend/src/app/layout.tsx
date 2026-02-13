import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Tamkin — Find the right people to make your stuff',
  description: 'Tamkin helps businesses find, vet, and manage suppliers with AI-powered mission workflows.',
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
