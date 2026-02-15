'use client'

import { useState } from 'react'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: () => void
}

interface OutreachRecord {
  supplier_id: string
  supplier_name: string
  recipient_email: string
  sent_at: string | null
  delivery_status: string
  opened: boolean
  opened_at: string | null
  responded: boolean
  responded_at: string | null
  bounced: boolean
}

interface LineItem {
  part_number: string
  description: string
  material_spec: string
  process_type: string
  annual_volume: number
  lot_size: number
}

interface RFQPackage {
  rfq_id: string
  rfq_date: string
  response_deadline: string
  buyer_company: string
  buyer_contact_name: string
  program_name: string | null
  line_items: LineItem[]
  quality_block: Record<string, unknown>
  delivery_schedule: Record<string, unknown>
  tooling_terms: Record<string, unknown>
  email_subject: string
  email_body: string
  nda_required: boolean
}

const STATUS_ICONS: Record<string, string> = {
  sent: '✉️',
  delivered: '✅',
  opened: '👁',
  bounced: '❌',
  pending: '⏳',
}

export default function RFQView({ data, isActive, onApprove }: Props) {
  const [showPreview, setShowPreview] = useState(false)

  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Preparing RFQ packages...</span>
        </div>
        <p className="text-xs text-zinc-600">Generating professional RFQ documents and email drafts</p>
      </div>
    )
  }

  const rfqPackage = (data.rfq_package || {}) as RFQPackage
  const outreach = (data.outreach_records || []) as OutreachRecord[]
  const totalSent = data.total_sent as number || 0
  const totalBounced = data.total_bounced as number || 0

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">RFQ & Outreach</h3>
          <p className="text-xs text-zinc-500 mt-1">
            {totalSent} sent • {totalBounced} bounced • {outreach.filter((o) => o.responded).length} responded
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700"
          >
            {showPreview ? 'Hide RFQ' : 'Preview RFQ'}
          </button>
          {isActive && (
            <button
              onClick={onApprove}
              className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
            >
              Send RFQs
            </button>
          )}
        </div>
      </div>

      {/* RFQ Preview */}
      {showPreview && rfqPackage.rfq_id && (
        <div className="px-6 py-5 border-b border-zinc-800 bg-zinc-800/20">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <span className="text-[10px] text-zinc-500 uppercase">RFQ ID</span>
              <p className="text-xs text-zinc-300 font-mono">{rfqPackage.rfq_id}</p>
            </div>
            <div>
              <span className="text-[10px] text-zinc-500 uppercase">Date</span>
              <p className="text-xs text-zinc-300">{rfqPackage.rfq_date}</p>
            </div>
            <div>
              <span className="text-[10px] text-zinc-500 uppercase">Deadline</span>
              <p className="text-xs text-zinc-300">{rfqPackage.response_deadline}</p>
            </div>
            <div>
              <span className="text-[10px] text-zinc-500 uppercase">NDA</span>
              <p className="text-xs text-zinc-300">{rfqPackage.nda_required ? 'Required' : 'Not Required'}</p>
            </div>
          </div>

          {/* Line items */}
          {rfqPackage.line_items.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Line Items</p>
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-700">
                    <th className="text-left py-1 text-zinc-500 font-normal">Part</th>
                    <th className="text-left py-1 text-zinc-500 font-normal">Description</th>
                    <th className="text-left py-1 text-zinc-500 font-normal">Material</th>
                    <th className="text-left py-1 text-zinc-500 font-normal">Process</th>
                    <th className="text-right py-1 text-zinc-500 font-normal">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {rfqPackage.line_items.map((item, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-1.5 text-zinc-300 font-mono">{item.part_number || `LI-${i + 1}`}</td>
                      <td className="py-1.5 text-zinc-400">{item.description}</td>
                      <td className="py-1.5 text-zinc-400">{item.material_spec}</td>
                      <td className="py-1.5 text-zinc-400">{item.process_type}</td>
                      <td className="py-1.5 text-zinc-300 text-right">{item.annual_volume.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Email preview */}
          {rfqPackage.email_subject && (
            <div className="bg-zinc-900/80 rounded-lg p-4">
              <p className="text-xs text-zinc-500 mb-1">Subject:</p>
              <p className="text-sm text-zinc-300 mb-3">{rfqPackage.email_subject}</p>
              <p className="text-xs text-zinc-500 mb-1">Body:</p>
              <pre className="text-xs text-zinc-400 whitespace-pre-wrap leading-relaxed font-sans">{rfqPackage.email_body}</pre>
            </div>
          )}
        </div>
      )}

      {/* Outreach tracker */}
      <div className="divide-y divide-zinc-800">
        {outreach.map((rec) => (
          <div key={rec.supplier_id} className="px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm">{STATUS_ICONS[rec.delivery_status] || '⏳'}</span>
              <div>
                <h4 className="text-sm font-medium text-zinc-200">{rec.supplier_name}</h4>
                <p className="text-xs text-zinc-500">{rec.recipient_email}</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs">
              {rec.sent_at && (
                <span className="text-zinc-500">Sent {new Date(rec.sent_at).toLocaleDateString()}</span>
              )}
              {rec.opened && (
                <span className="text-emerald-400">Opened</span>
              )}
              {rec.responded && (
                <span className="text-amber-400 font-semibold">Responded</span>
              )}
              {rec.bounced && (
                <span className="text-red-400">Bounced</span>
              )}
              {!rec.sent_at && (
                <span className="text-zinc-600">Pending</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {outreach.length === 0 && (
        <div className="px-6 py-8 text-center">
          <p className="text-sm text-zinc-500">RFQ package ready. Approve to send to suppliers.</p>
        </div>
      )}
    </div>
  )
}
