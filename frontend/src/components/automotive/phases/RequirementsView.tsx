'use client'

import { useState } from 'react'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (edits?: Record<string, unknown>) => void
}

const FIELD_LABELS: Record<string, string> = {
  part_description: 'Part Description',
  part_category: 'Part Category',
  material_family: 'Material Family',
  material_spec: 'Material Specification',
  manufacturing_process: 'Manufacturing Process',
  secondary_operations: 'Secondary Operations',
  annual_volume: 'Annual Volume',
  lot_size: 'Lot Size',
  volume_confidence: 'Volume Confidence',
  tolerances: 'Tolerances',
  surface_finish: 'Surface Finish',
  certifications_required: 'Certifications Required',
  ppap_level: 'PPAP Level',
  preferred_regions: 'Preferred Regions',
  geographic_constraints: 'Geographic Constraints',
  buyer_plant_location: 'Buyer Plant Location',
  urgency: 'Urgency',
  prototype_needed: 'Prototype Needed',
  complexity_score: 'Complexity',
  estimated_tooling_range: 'Estimated Tooling Cost',
  estimated_lead_time: 'Estimated Lead Time',
}

export default function RequirementsView({ data, isActive, onApprove }: Props) {
  const [editing, setEditing] = useState(false)

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

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="font-semibold">Parsed Requirements</h3>
        {isActive && (
          <div className="flex gap-2">
            <button
              onClick={() => setEditing(!editing)}
              className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700"
            >
              {editing ? 'Cancel Edit' : 'Edit'}
            </button>
            <button
              onClick={() => onApprove()}
              className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
            >
              Confirm & Search
            </button>
          </div>
        )}
      </div>

      {/* Ambiguities banner */}
      {ambiguities.length > 0 && (
        <div className="px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
          <p className="text-sm text-amber-400 font-medium mb-1">Needs Clarification</p>
          <ul className="text-xs text-amber-300/80 space-y-1">
            {ambiguities.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Fields grid */}
      <div className="p-6 grid grid-cols-2 gap-4">
        {Object.entries(FIELD_LABELS).map(([key, label]) => {
          const value = data[key]
          if (value === null || value === undefined || value === '') return null

          const display = Array.isArray(value)
            ? value.join(', ')
            : typeof value === 'boolean'
              ? value ? 'Yes' : 'No'
              : String(value)

          const isInferred = key === 'geographic_constraints' && display.includes('inferred')

          return (
            <div key={key} className="group">
              <label className="text-xs text-zinc-500 uppercase tracking-wider">{label}</label>
              <div className={`mt-1 text-sm ${isInferred ? 'text-amber-400' : 'text-zinc-200'}`}>
                {display}
                {isInferred && <span className="ml-2 text-xs text-amber-500">(inferred)</span>}
              </div>
            </div>
          )
        })}
      </div>

      {/* Estimates section */}
      {(data.estimated_tooling_range || data.estimated_lead_time) && (
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/50">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Market Estimates</p>
          <div className="flex gap-6">
            {data.estimated_tooling_range && (
              <div>
                <span className="text-xs text-zinc-500">Tooling:</span>
                <span className="ml-2 text-sm text-zinc-300">{String(data.estimated_tooling_range)}</span>
              </div>
            )}
            {data.estimated_lead_time && (
              <div>
                <span className="text-xs text-zinc-500">Lead Time:</span>
                <span className="ml-2 text-sm text-zinc-300">{String(data.estimated_lead_time)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
