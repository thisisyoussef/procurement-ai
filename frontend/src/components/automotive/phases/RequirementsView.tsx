'use client'

import { useState, useCallback } from 'react'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (edits?: Record<string, unknown>) => void
}

/* ── field definitions ── */

interface FieldDef {
  label: string
  type: 'text' | 'number' | 'select' | 'list' | 'boolean'
  options?: string[] // for select fields
  wide?: boolean     // span 2 columns
}

const FIELDS: Record<string, FieldDef> = {
  part_description:       { label: 'Part Description', type: 'text', wide: true },
  part_category:          { label: 'Category', type: 'select', options: ['stamping','die_casting','injection_molding','cnc_machining','forging','pcba','wiring_harness','rubber_sealing','assembly','other'] },
  material_family:        { label: 'Material Family', type: 'text' },
  material_spec:          { label: 'Material Spec', type: 'text' },
  manufacturing_process:  { label: 'Mfg Process', type: 'text' },
  secondary_operations:   { label: 'Secondary Ops', type: 'list' },
  annual_volume:          { label: 'Annual Volume', type: 'number' },
  lot_size:               { label: 'Lot Size', type: 'number' },
  volume_confidence:      { label: 'Volume Confidence', type: 'select', options: ['exact','estimated','unknown'] },
  tolerances:             { label: 'Tolerances', type: 'text' },
  surface_finish:         { label: 'Surface Finish', type: 'text' },
  certifications_required:{ label: 'Certifications', type: 'list' },
  ppap_level:             { label: 'PPAP Level', type: 'select', options: ['1','2','3','4','5'] },
  preferred_regions:      { label: 'Preferred Regions', type: 'list' },
  geographic_constraints: { label: 'Geo Constraints', type: 'text' },
  buyer_plant_location:   { label: 'Plant Location', type: 'text' },
  urgency:                { label: 'Urgency', type: 'select', options: ['standard','expedited','urgent'] },
  prototype_needed:       { label: 'Prototype Needed', type: 'boolean' },
  prototype_quantity:     { label: 'Prototype Qty', type: 'number' },
  complexity_score:       { label: 'Complexity', type: 'select', options: ['simple','moderate','complex'] },
}

/* ── helpers ── */

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return (value as string[]).join(', ')
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

/* ── component ── */

export default function RequirementsView({ data, isActive, onApprove }: Props) {
  const [editing, setEditing] = useState(false)
  const [edits, setEdits] = useState<Record<string, unknown>>({})
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const updateField = useCallback((key: string, value: unknown) => {
    setEdits(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleConfirm = async () => {
    setSubmitting(true)
    // Merge answers into edits as notes
    const answeredAmbiguities = Object.entries(answers)
      .filter(([, v]) => v.trim())
      .map(([idx, v]) => `Q: ${(data?.ambiguities as string[])?.[Number(idx)]} → A: ${v}`)

    const finalEdits = {
      ...edits,
      ...(answeredAmbiguities.length > 0 ? { clarification_notes: answeredAmbiguities } : {}),
    }

    const hasEdits = Object.keys(finalEdits).length > 0
    onApprove(hasEdits ? finalEdits : undefined)
    setSubmitting(false)
  }

  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Parsing your requirements...</span>
        </div>
        <p className="text-xs text-zinc-600">Analyzing procurement request with AI</p>
      </div>
    )
  }

  const ambiguities = (data.ambiguities as string[]) || []

  // Current value = edit override or original
  const val = (key: string) => (key in edits ? edits[key] : data[key])
  const edited = (key: string) => key in edits && edits[key] !== data[key]

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Parsed Requirements</h3>
          {editing && (
            <p className="text-xs text-zinc-500 mt-0.5">Click any field to edit · changes highlighted in amber</p>
          )}
        </div>
        {isActive && (
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (editing) { setEdits({}); setAnswers({}) }
                setEditing(!editing)
              }}
              className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors"
            >
              {editing ? 'Cancel' : 'Edit Fields'}
            </button>
            <button
              onClick={handleConfirm}
              disabled={submitting}
              className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : editing && Object.keys(edits).length > 0 ? 'Save & Continue →' : 'Approve & Continue →'}
            </button>
          </div>
        )}
      </div>

      {/* Clarification questions with input fields */}
      {ambiguities.length > 0 && (
        <div className="px-6 py-4 bg-amber-500/5 border-b border-amber-500/20">
          <div className="flex items-center gap-2 mb-3">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="#f59e0b" strokeWidth="1.5"/>
              <path d="M8 5v3M8 10.5v.5" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <p className="text-sm text-amber-400 font-medium">
              {ambiguities.length} question{ambiguities.length > 1 ? 's' : ''} to clarify
            </p>
            <span className="text-xs text-zinc-500">(optional — skip to continue with defaults)</span>
          </div>
          <div className="space-y-3">
            {ambiguities.map((q, i) => (
              <div key={i} className="flex gap-3 items-start">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center mt-0.5 font-medium">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-amber-300/80 mb-1.5">{q}</p>
                  <input
                    type="text"
                    value={answers[i] || ''}
                    onChange={(e) => setAnswers(prev => ({ ...prev, [i]: e.target.value }))}
                    placeholder="Type your answer (or leave blank to skip)..."
                    className="w-full bg-zinc-800/80 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-amber-500/40 focus:border-amber-500/40"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fields grid */}
      <div className="p-6 grid grid-cols-2 gap-x-6 gap-y-4">
        {Object.entries(FIELDS).map(([key, def]) => {
          const value = val(key)
          if (!editing && (value === null || value === undefined || value === '')) return null

          const isEdited = edited(key)

          return (
            <div key={key} className={def.wide ? 'col-span-2' : ''}>
              <label className={`text-xs uppercase tracking-wider ${isEdited ? 'text-amber-400' : 'text-zinc-500'}`}>
                {def.label}
                {isEdited && <span className="ml-1 normal-case tracking-normal">(edited)</span>}
              </label>

              {editing ? (
                <div className="mt-1">
                  {def.type === 'text' && (
                    <input
                      type="text"
                      value={String(val(key) ?? '')}
                      onChange={(e) => updateField(key, e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                    />
                  )}
                  {def.type === 'number' && (
                    <input
                      type="number"
                      value={val(key) !== null && val(key) !== undefined ? String(val(key)) : ''}
                      onChange={(e) => updateField(key, e.target.value ? Number(e.target.value) : null)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                    />
                  )}
                  {def.type === 'select' && (
                    <select
                      value={String(val(key) ?? '')}
                      onChange={(e) => updateField(key, e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                    >
                      <option value="">—</option>
                      {def.options?.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  )}
                  {def.type === 'list' && (
                    <input
                      type="text"
                      value={Array.isArray(val(key)) ? (val(key) as string[]).join(', ') : String(val(key) ?? '')}
                      onChange={(e) => updateField(key, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                      placeholder="Comma-separated values"
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
                    />
                  )}
                  {def.type === 'boolean' && (
                    <button
                      onClick={() => updateField(key, !val(key))}
                      className={`mt-0.5 px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                        val(key)
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                      }`}
                    >
                      {val(key) ? 'Yes' : 'No'}
                    </button>
                  )}
                </div>
              ) : (
                <div className={`mt-1 text-sm ${isEdited ? 'text-amber-400' : 'text-zinc-200'}`}>
                  {displayValue(value)}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Estimates section (read-only) */}
      {!!(data.estimated_tooling_range || data.estimated_lead_time) && (
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Market Estimates</p>
          <div className="flex gap-6">
            {!!data.estimated_tooling_range && (
              <div>
                <span className="text-xs text-zinc-500">Tooling:</span>
                <span className="ml-2 text-sm text-zinc-300">{String(data.estimated_tooling_range)}</span>
              </div>
            )}
            {!!data.estimated_lead_time && (
              <div>
                <span className="text-xs text-zinc-500">Lead Time:</span>
                <span className="ml-2 text-sm text-zinc-300">{String(data.estimated_lead_time)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick approve bar when not editing */}
      {isActive && !editing && (
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-950/50 flex items-center justify-between">
          <p className="text-xs text-zinc-500">
            Looks good? Approve to start supplier discovery, or edit fields above.
          </p>
          <button
            onClick={handleConfirm}
            disabled={submitting}
            className="px-5 py-2 bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400 transition-colors text-sm disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Approve & Continue →'}
          </button>
        </div>
      )}
    </div>
  )
}
