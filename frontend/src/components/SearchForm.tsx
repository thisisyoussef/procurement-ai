'use client'

import { useState } from 'react'

interface SearchFormProps {
  onSearch: (description: string) => void
  loading: boolean
}

const EXAMPLES = [
  'I need 500 custom canvas tote bags, 14x16 inches, 12oz cotton canvas, screen printed with my logo in 2 colors, delivered to LA by March 2026',
  '1000 custom enamel pins, 1.5 inch, die struck soft enamel, butterfly clutch backing, need them for a music festival in Austin TX by June',
  'Looking for a PCB manufacturer for 200 custom Arduino shields, 2-layer FR-4, lead-free HASL finish, shipped to NYC',
]

export default function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim() || loading) return
    onSearch(description.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
      <div className="relative">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what you need manufactured or sourced..."
          rows={4}
          className="w-full p-4 pr-28 border border-slate-300 rounded-xl shadow-sm
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     resize-none text-slate-900 placeholder:text-slate-400"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!description.trim() || loading}
          className="absolute right-3 bottom-3 px-5 py-2.5 bg-blue-600 text-white
                     rounded-lg font-medium text-sm hover:bg-blue-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Searching...
            </span>
          ) : (
            'Find Suppliers'
          )}
        </button>
      </div>

      {!loading && (
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs text-slate-500 py-1">Try:</span>
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setDescription(ex)}
              className="text-xs px-3 py-1 bg-slate-100 text-slate-600
                         rounded-full hover:bg-slate-200 transition-colors
                         truncate max-w-xs"
            >
              {ex.slice(0, 60)}...
            </button>
          ))}
        </div>
      )}
    </form>
  )
}
