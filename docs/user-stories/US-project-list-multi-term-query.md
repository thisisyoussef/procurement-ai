## User Story: Project List Multi-Term Query Matching

As a signed-in procurement manager
I want project-list search to support multi-term queries
So that I can quickly find projects even when key words are separated in title/description text

## Acceptance Criteria

### Case 1: Non-contiguous multi-term title match
Given I own projects titled `Bottle supplier shortlist for stainless steel run` and `Luxury Candle Labels`
When I request `GET /api/v1/projects?q=stainless bottle`
Then the response includes only `Bottle supplier shortlist for stainless steel run`.

### Case 2: Multi-term matching across title and description
Given I own a project titled `Container supplier shortlist` with description `Need food-grade lids for shipment`
When I request `GET /api/v1/projects?q=container lids`
Then that project is returned even though the terms are split across title and description.

### Case 3: All terms are required
Given I own a project matching only part of a query
When I request `GET /api/v1/projects?q=bottle gasket`
Then no projects are returned unless both `bottle` and `gasket` terms are present in title and/or description.
