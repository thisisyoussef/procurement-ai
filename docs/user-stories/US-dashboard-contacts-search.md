# US: Dashboard Contacts Meaningful Query Guardrail

As a returning procurement user
I want dashboard contacts search to require at least two meaningful characters
So that accidental one-character filters do not return noisy broad results

## Acceptance Criteria

### Scenario 1: Valid keyword filters contacts
Given I am authenticated and open `GET /api/v1/dashboard/contacts?q=acme`
When supplier contacts include mixed names and emails
Then only contacts matching the keyword (case-insensitive) are returned.

### Scenario 2: Whitespace-only query stays unfiltered
Given I pass whitespace-only query text to `GET /api/v1/dashboard/contacts?q=%20%20%20`
When the endpoint normalizes query input
Then the query is treated as empty and returns the unfiltered contact list.

### Scenario 3: Effective one-character query is rejected
Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?q=a` (or a trimmed equivalent like `%20a%20`)
Then the API responds with `422 Unprocessable Entity` and an actionable validation detail.
