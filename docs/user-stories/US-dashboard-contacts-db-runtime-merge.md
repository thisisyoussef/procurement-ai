As a dashboard user
I want dashboard contacts to include both historical DB contacts and newly discovered runtime suppliers
So that I can start outreach without missing suppliers that have not yet generated interaction rows.

Acceptance criteria

Given DB contacts exist for my account and runtime discovery has additional unique suppliers
When I request `GET /api/v1/dashboard/contacts`
Then the response includes deduplicated contacts from both sources up to the requested `limit`.

Given a supplier appears in both DB and runtime contact sources
When contacts are merged
Then the supplier appears only once and preserves richer data (for example missing website/email fields are filled and latest project context is kept).

Given I request `GET /api/v1/dashboard/contacts?q=acme&limit=1`
When only Acme-matching contacts are considered across both sources
Then the API returns one deduplicated Acme contact and does not consume the limit with non-matching entries.
