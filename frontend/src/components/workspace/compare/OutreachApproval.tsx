'use client'

interface SelectedSupplierRow {
  idx: number
  supplier: any
  comparison?: any
}

interface OutreachApprovalProps {
  selectedSuppliers: SelectedSupplierRow[]
  selectedSupplierIndices: number[]
  plainLanguagePreview: string[]
  approvalLoading: boolean
  approvalError: string | null
  approvalSuccess: string | null
  onToggleSupplier: (supplierIndex: number) => void
  onOpenSupplierProfile: (supplierIndex: number) => void
  onConfirmSend: () => void
  onBackToVerdict: () => void
}

export default function OutreachApproval({
  selectedSuppliers,
  selectedSupplierIndices,
  plainLanguagePreview,
  approvalLoading,
  approvalError,
  approvalSuccess,
  onToggleSupplier,
  onOpenSupplierProfile,
  onConfirmSend,
  onBackToVerdict,
}: OutreachApprovalProps) {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-5">
      <button
        type="button"
        onClick={onBackToVerdict}
        className="text-[12px] text-teal hover:text-teal-600 transition-colors flex items-center gap-1"
      >
        <span>&larr;</span> Back to recommendation
      </button>

      <div className="card p-6 space-y-4">
        <div>
          <h2 className="font-heading text-2xl text-ink">Ready to reach out</h2>
          <p className="mt-1 text-[12px] text-ink-3">
            Confirm suppliers and message intent before Procurement AI sends outreach.
          </p>
        </div>

        <div className="space-y-2">
          {selectedSuppliers.map((row) => {
            const selected = selectedSupplierIndices.includes(row.idx)
            return (
              <label
                key={row.idx}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 ${
                  selected ? 'border-teal bg-teal/5' : 'border-surface-3 bg-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onToggleSupplier(row.idx)}
                    className="accent-teal"
                  />
                  <button
                    type="button"
                    onClick={() => onOpenSupplierProfile(row.idx)}
                    className="text-[12px] font-medium text-ink hover:text-teal transition-colors"
                  >
                    {row.supplier?.name || `Supplier ${row.idx + 1}`}
                  </button>
                </div>
                <span className="text-[11px] text-ink-4">
                  {row.comparison?.estimated_unit_cost || row.comparison?.overall_score || 'pending'}
                </span>
              </label>
            )
          })}
        </div>

        {plainLanguagePreview.length > 0 && (
          <div className="rounded-xl border border-surface-3 bg-surface-2/40 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[1.4px] text-ink-4 mb-2">
              Message preview
            </p>
            <div className="space-y-2">
              {plainLanguagePreview.slice(0, 2).map((line, idx) => (
                <p key={idx} className="text-[12px] text-ink-3 leading-relaxed">
                  {line}
                </p>
              ))}
            </div>
          </div>
        )}

        {approvalError && (
          <p className="text-[12px] text-red-600">{approvalError}</p>
        )}
        {approvalSuccess && (
          <p className="text-[12px] text-teal">{approvalSuccess}</p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onConfirmSend}
            disabled={approvalLoading || selectedSupplierIndices.length === 0}
            className="rounded-lg bg-teal px-4 py-2 text-[12px] font-medium text-white disabled:opacity-50"
          >
            {approvalLoading ? 'Sending...' : 'Confirm & send'}
          </button>
          <button
            type="button"
            onClick={onBackToVerdict}
            className="rounded-lg border border-surface-3 px-4 py-2 text-[12px] text-ink-3 hover:bg-surface-2 transition-colors"
          >
            Keep reviewing
          </button>
        </div>
      </div>
    </div>
  )
}
