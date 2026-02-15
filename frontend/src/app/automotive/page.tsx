'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { automotiveClient } from '@/lib/automotive/client'
import { STAGE_LABELS, STAGE_ORDER, type PipelineStage } from '@/types/automotive'

export default function AutomotiveDashboard() {
  const router = useRouter()
  const [request, setRequest] = useState('')
  const [buyerCompany, setBuyerCompany] = useState('')
  const [buyerName, setBuyerName] = useState('')
  const [buyerEmail, setBuyerEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [projects, setProjects] = useState<any[]>([])
  const [loaded, setLoaded] = useState(false)

  const loadProjects = async () => {
    try {
      const list = await automotiveClient.listProjects()
      setProjects(list)
    } catch (e) {
      console.error('Failed to load projects', e)
    }
    setLoaded(true)
  }

  if (!loaded) {
    loadProjects()
  }

  const handleCreate = async () => {
    if (!request.trim()) return
    setLoading(true)
    try {
      const result = await automotiveClient.createProject({
        raw_request: request,
        buyer_company: buyerCompany,
        buyer_contact_name: buyerName,
        buyer_contact_email: buyerEmail,
      })
      router.push(`/automotive/project?id=${result.project_id}`)
    } catch (e) {
      console.error('Failed to create project', e)
    }
    setLoading(false)
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-12">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-amber-400">Tamkin</span> Automotive
          </h1>
          <p className="text-zinc-400 mt-1">
            AI-Powered Supplier Intelligence for the Automotive Supply Chain
          </p>
        </div>
      </div>

      {/* New Project Card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 mb-10">
        <h2 className="text-xl font-semibold mb-2">New Procurement Project</h2>
        <p className="text-zinc-400 text-sm mb-6">
          Describe what you need — Tamkin will find, vet, and compare suppliers for you.
        </p>

        <textarea
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder='e.g. "I need a Tier 2 supplier for aluminum die-cast EV battery housings, 50K annual volume, IATF 16949 required, preferably in Mexico for USMCA compliance"'
          className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40 resize-none h-28"
        />

        <div className="grid grid-cols-3 gap-4 mt-4">
          <input
            value={buyerCompany}
            onChange={(e) => setBuyerCompany(e.target.value)}
            placeholder="Your company name"
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40"
          />
          <input
            value={buyerName}
            onChange={(e) => setBuyerName(e.target.value)}
            placeholder="Your name"
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40"
          />
          <input
            value={buyerEmail}
            onChange={(e) => setBuyerEmail(e.target.value)}
            placeholder="Your email"
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40"
          />
        </div>

        <button
          onClick={handleCreate}
          disabled={loading || !request.trim()}
          className="mt-4 px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? 'Starting...' : 'Start Sourcing'}
        </button>
      </div>

      {/* Active Projects */}
      {projects.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Active Projects</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((p) => (
              <button
                key={p.project_id}
                onClick={() => router.push(`/automotive/project?id=${p.project_id}`)}
                className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-left hover:border-amber-500/40 transition-colors"
              >
                <p className="text-sm text-zinc-300 line-clamp-2 mb-3">{p.raw_request}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-1 rounded-full bg-zinc-800 text-amber-400 font-medium">
                    {STAGE_LABELS[p.current_stage as PipelineStage] || p.current_stage}
                  </span>
                  {p.buyer_company && (
                    <span className="text-xs text-zinc-500">{p.buyer_company}</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {loaded && projects.length === 0 && (
        <div className="text-center text-zinc-500 py-12">
          <p>No projects yet. Describe your sourcing need above to get started.</p>
        </div>
      )}
    </div>
  )
}
