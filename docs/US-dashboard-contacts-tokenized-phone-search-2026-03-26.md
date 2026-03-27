# User Story: Tokenized Dashboard Contact Search with Phone-Digit Support

As a procurement founder
I want dashboard contact search to match multiple terms and digit-only phone input
So that I can quickly find suppliers even when contact data uses mixed formatting.

## Acceptance Criteria

1. Given a dashboard contact with name "Acme Precision Metals" and city "Detroit"
When I search `acme detroit`
Then the supplier appears in `/api/v1/dashboard/contacts` results.

2. Given a dashboard contact with phone `+1 (312) 555-0142`
When I search `3125550142`
Then the supplier appears in `/api/v1/dashboard/contacts` results whether the row comes from DB-backed interactions or runtime discovery data.

3. Given a dashboard contact with name "Acme Precision Metals" and city "Detroit"
When I search `acme toronto`
Then the supplier is excluded because all query tokens must be satisfied.
