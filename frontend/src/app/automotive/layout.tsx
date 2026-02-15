import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tamkin Automotive — AI-Powered Supplier Intelligence',
  description: 'Find, vet, compare, and connect with automotive suppliers using AI.',
}

export default function AutomotiveLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {children}
    </div>
  )
}
