As a sourcing manager comparing international suppliers for heavy products
I want unrealistically low per-unit freight estimates to be converted into quote-required outcomes
So that I do not make decisions based on misleading landed-cost assumptions.

Acceptance criteria

Given a heavy or industrial product and an international supplier lane
When the comparison output contains a tiny per-unit shipping estimate (for example `$0.30-$0.80 per unit`) at moderate quantity
Then the comparison row shipping value is converted to `Freight quote required`, landed cost is set to `Freight quote required to finalize landed cost`, and the weakness list explains the freight assumption risk.

Given the same heavy international lane but high-volume quantity (for example `50000` units)
When the comparison output includes low per-unit shipping
Then the shipping and landed-cost values remain unchanged.

Given a domestic supplier lane for the same heavy product
When the comparison output includes low per-unit shipping
Then the shipping and landed-cost values remain unchanged and no quote-required conversion note is appended to analysis.
