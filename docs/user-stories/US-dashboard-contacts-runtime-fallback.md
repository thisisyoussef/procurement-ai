As a procurement manager
I want dashboard contacts to still load when the contacts table is unavailable or empty
So that I can continue outreach using supplier contacts already discovered in my projects.

Acceptance criteria

Given the DB contacts query fails
When I request `GET /api/v1/dashboard/contacts`
Then the API returns contacts derived from my runtime project discovery results instead of an empty response.

Given runtime fallback is used and I provide `q=acme` with `limit=1`
When only one supplier matches the query across runtime contacts
Then that matching supplier is returned even if non-matching suppliers appear first in raw discovery order.

Given the same supplier appears in multiple projects I own
When runtime fallback derives dashboard contacts
Then the supplier appears once with aggregated `interaction_count`/`project_count` and uses the most recent project as `last_project_id`.
