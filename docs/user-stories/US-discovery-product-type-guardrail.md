# US: Discovery Product-Type Guardrail

As a procurement manager
I want supplier discovery to filter out off-category suppliers
So that I can compare vendors that actually manufacture my requested product

## Acceptance Criteria

### Scenario 1: Exclude off-category supplier-memory candidates
Given I am sourcing `heavyweight hoodies`
When discovery merges supplier-memory candidates that only mention packaging services
Then those packaging-only candidates are returned in `filtered_suppliers` with `filtered_reason` set to `wrong_product_type`

### Scenario 2: Keep on-category candidates
Given I am sourcing `heavyweight hoodies`
When discovery processes candidates that explicitly mention hoodies or apparel manufacturing
Then those candidates remain in the main `suppliers` list

### Scenario 3: Do not over-filter sparse legacy records
Given a supplier-memory record has minimal metadata (no categories and no description)
When discovery cannot confidently determine category mismatch
Then the supplier remains eligible in the main `suppliers` list
