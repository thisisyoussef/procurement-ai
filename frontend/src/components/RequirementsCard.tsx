'use client'

interface RequirementsCardProps {
  requirements: {
    product_type: string
    material: string | null
    dimensions: string | null
    quantity: number | null
    customization: string | null
    delivery_location: string | null
    deadline: string | null
    certifications_needed: string[]
    budget_range: string | null
    missing_fields: string[]
  }
}

export default function RequirementsCard({ requirements }: RequirementsCardProps) {
  const fields = [
    { label: 'Product', value: requirements.product_type },
    { label: 'Material', value: requirements.material },
    { label: 'Dimensions', value: requirements.dimensions },
    { label: 'Quantity', value: requirements.quantity?.toLocaleString() },
    { label: 'Customization', value: requirements.customization },
    { label: 'Delivery to', value: requirements.delivery_location },
    { label: 'Deadline', value: requirements.deadline },
    { label: 'Budget', value: requirements.budget_range },
  ].filter((f) => f.value)

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 mb-4">
        Parsed Requirements
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {fields.map((f) => (
          <div key={f.label}>
            <p className="text-xs text-slate-500 uppercase tracking-wider">{f.label}</p>
            <p className="text-sm font-medium text-slate-800 mt-0.5">{f.value}</p>
          </div>
        ))}
      </div>

      {requirements.certifications_needed.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Certifications Needed</p>
          <div className="flex gap-2 mt-1">
            {requirements.certifications_needed.map((c) => (
              <span key={c} className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-full">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      {requirements.missing_fields.length > 0 && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-xs text-amber-700">
            Missing information: {requirements.missing_fields.join(', ')}. Results may be more accurate with these details.
          </p>
        </div>
      )}
    </div>
  )
}
