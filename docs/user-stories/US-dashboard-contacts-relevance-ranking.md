As a procurement manager comparing suppliers in the dashboard
I want contact results to prioritize suppliers seen across more projects when interaction counts are tied
So that the most broadly relevant suppliers appear first for follow-up.

Acceptance criteria

Given two supplier contacts have the same `interaction_count`
When `GET /api/v1/dashboard/contacts` returns merged DB and runtime contacts
Then the supplier with higher `project_count` is listed first.

Given two supplier contacts have the same `interaction_count` and `project_count`
When `GET /api/v1/dashboard/contacts` returns merged contacts
Then the supplier with the newer `last_interaction_at` is listed first.

Given two supplier contacts tie on `interaction_count`, `project_count`, and `last_interaction_at`
When `GET /api/v1/dashboard/contacts` returns merged contacts
Then suppliers are ordered alphabetically by name as the final tie-breaker.
