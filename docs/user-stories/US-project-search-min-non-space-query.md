As a procurement manager
I want project search queries to require a minimum meaningful length
So that dashboard and project list results are not filtered by accidental one-character input

## Acceptance Criteria
1. Given I call `GET /api/v1/projects?q=%20a%20`, when the API validates the query, then it returns `422` with `Query must include at least 2 non-space characters.`
2. Given I call `GET /api/v1/dashboard/summary?q=%20a%20`, when the API validates the query, then it returns `422` with `Query must include at least 2 non-space characters.`
3. Given I call `GET /api/v1/projects?q=%20%20%20`, when the API normalizes the query, then whitespace-only input is treated as no query and projects are returned without keyword filtering.
4. Given I call `GET /api/v1/projects?q=aa`, when the API validates and applies the filter, then it returns `200` and filters results by that keyword.
