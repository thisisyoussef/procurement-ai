As a procurement operator managing many sourcing runs
I want project search to support multi-term matching across title and description
So that I can quickly find the exact project using a combination of product and context keywords.

Acceptance criteria

Given I am authenticated and call `GET /api/v1/projects?q=bottle%20labels`
When one project contains `bottle` in the title and `labels` in the product description
Then that project is returned because all query terms match across searchable project fields.

Given I am authenticated and call `GET /api/v1/dashboard/summary?q=bottle%20labels`
When no project contains every query term across title and description
Then the dashboard response excludes partial matches and returns no matching projects.

Given I am authenticated and call either endpoint with mixed-case multi-term input like `q=BoTtLe%20LaBeLs`
When the stored project text is lowercase or differently cased
Then matching remains case-insensitive and the relevant project is returned.
