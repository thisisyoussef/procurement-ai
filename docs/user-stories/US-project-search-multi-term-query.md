# User Story: Project search multi-term matching

As a buyer running multiple sourcing projects
I want project search to support multi-term matching across title and description
So that I can quickly find the right run even when keywords are split across fields

## Acceptance Criteria

### Scenario 1: Match all terms in title
Given I am authenticated and have projects with titles "Bottle labels supplier shortlist" and "Bottle source run"
When I request `GET /api/v1/projects?q=bottle%20shortlist`
Then only the shortlist project is returned.

### Scenario 2: Match terms across title and description
Given I am authenticated and a project has title "Bottle source run" and description "Need premium matte labels"
When I request `GET /api/v1/dashboard/summary?q=bottle%20labels`
Then that project is returned because all terms match across title and description.

### Scenario 3: Require all terms
Given I am authenticated and a project only matches one query term
When I request `GET /api/v1/projects?q=bottle%20shortlist`
Then no project is returned.
