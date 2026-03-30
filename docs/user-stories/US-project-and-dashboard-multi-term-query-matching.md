# User Story: Multi-Term Project Search Matching

As a procurement manager
I want project search to require all query terms across project title and description
So that I can quickly find the exact sourcing run I need without broad false-positive results

## Acceptance Criteria

1. Given my projects contain overlapping words,
When I call `GET /api/v1/projects?q=motor aluminum`,
Then only projects containing both `motor` and `aluminum` in title/description are returned.

2. Given a valid multi-term search,
When I change query term order/case (for example `q=ALUMINUM motor`),
Then the same matching project set is returned.

3. Given a status-scoped search,
When I call `GET /api/v1/projects?status=discovering&q=motor aluminum`,
Then results include only projects that satisfy both status and all query terms.

4. Given dashboard summary search,
When I call `GET /api/v1/dashboard/summary?q=motor aluminum`,
Then dashboard cards include only projects whose title/description contains all terms.

5. Given dashboard summary search with status,
When I call `GET /api/v1/dashboard/summary?status=discovering&q=motor aluminum`,
Then only projects matching both status and all terms are returned.
