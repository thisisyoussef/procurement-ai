As a sourcing operator
I want dashboard contacts search to support multi-keyword matching
So that I can quickly find the exact supplier contact without scrolling through broad matches

Acceptance Criteria
1. Given a supplier contact named "Acme Precision Metals" in Detroit
   When I search dashboard contacts with `q=acme detroit`
   Then that supplier is returned because both terms are matched across supported fields.

2. Given a supplier contact named "Acme Precision Metals" in Detroit
   When I search dashboard contacts with `q=acme toronto`
   Then that supplier is not returned because not all query terms match.

3. Given a supplier contact with phone `+1 (312) 555-0142`
   When I search dashboard contacts with `q=acme 3125550142`
   Then that supplier is returned because text and digit-only phone terms are both matched.
