# User Story: Tokenized Multi-Term Project Search

As a procurement manager
I want project search to match multiple keywords across title and description
So that I can quickly find the right sourcing run without typing exact phrases

## Acceptance Criteria

1. Given a project where one query term appears in the title and another appears in the description, when I call `GET /api/v1/projects?q=<term1> <term2>`, then the project is returned.
2. Given a query containing punctuation and irregular spacing, when I call `GET /api/v1/projects` or `GET /api/v1/dashboard/summary` with that query, then matching still works as if punctuation and extra spaces were ignored.
3. Given a query where one token is not present in either title or description, when I call project list or dashboard summary with that query, then the project is not returned.

## Implementation Notes

- Added tokenized query matching helpers in `app/api/v1/projects.py` and `app/services/dashboard_service.py`.
- Updated list and dashboard summary filtering to require all normalized query tokens.
- Added API tests covering cross-field token matching, punctuation/spacing tolerance, and all-token-required behavior.
