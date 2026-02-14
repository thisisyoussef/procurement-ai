'use client'

import type { SupplierProfileQuote } from '@/types/supplierProfile'

interface Props {
  quote: SupplierProfileQuote
  name: string
}

export default function ProfileQuote({ quote, name }: Props) {
  const { unit_price, currency, moq, lead_time, payment_terms, shipping_terms, validity_period, notes, source, quantity } = quote

  // Compute total if we have both unit price and quantity
  const numericPrice = unit_price ? parseFloat(unit_price.replace(/[^0-9.]/g, '')) : null
  const total = numericPrice && quantity ? (numericPrice * quantity).toLocaleString('en-US', { style: 'currency', currency: currency || 'USD' }) : null

  // Build a product description from available data
  const productDesc = quantity ? `${quantity} units` : 'Quote details'

  return (
    <div className="bg-surface border border-black/[.06] rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-7 py-5 border-b border-black/[.06] flex items-center justify-between">
        <h3 className="font-heading text-[20px] font-normal">
          {productDesc}
        </h3>
        {unit_price && (
          <div className="font-heading text-[32px] tracking-tight text-teal">
            {unit_price.startsWith('$') ? unit_price : `$${unit_price}`}
          </div>
        )}
      </div>

      {/* Quote rows */}
      <div className="px-7 py-1">
        {moq && <QuoteRow label="Minimum order quantity" value={moq} />}
        {lead_time && <QuoteRow label="Lead time" value={lead_time} />}
        {payment_terms && <QuoteRow label="Payment terms" value={payment_terms} />}
        {shipping_terms && <QuoteRow label="Shipping terms" value={shipping_terms} />}
        {currency && currency !== 'USD' && <QuoteRow label="Currency" value={currency} />}
        {notes && <QuoteRow label="Notes" value={notes} />}
      </div>

      {/* Footer */}
      <div className="px-7 py-5 bg-teal/[.02] border-t border-black/[.06] flex items-center justify-between flex-wrap gap-3">
        <div className="text-[12.5px] text-ink-3 leading-relaxed">
          {total && <><strong className="text-ink-2">Total: {total}</strong> &middot; </>}
          <span className={`inline-flex items-center gap-1 ${source === 'parsed_response' ? 'text-teal' : 'text-ink-4'}`}>
            {source === 'parsed_response' ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-teal" />
                Quoted by {name}
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-ink-4" />
                AI estimate
              </>
            )}
          </span>
          {validity_period && <> &middot; Valid for {validity_period}</>}
        </div>
        {source === 'parsed_response' && (
          <button className="px-4 py-2 rounded-[10px] text-[11px] font-semibold bg-teal text-white hover:shadow-[0_4px_12px_rgba(0,201,167,.15)] transition-all">
            Accept quote
          </button>
        )}
      </div>
    </div>
  )
}

function QuoteRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-3.5 text-[13.5px] border-b border-black/[.06] last:border-b-0">
      <span className="text-ink-3">{label}</span>
      <span className="font-semibold text-ink-2">{value}</span>
    </div>
  )
}
