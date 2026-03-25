As a procurement manager
I want project search to match project IDs
So that I can quickly find a project from shared IDs in messages or support threads

## Acceptance Criteria

1. Given I own multiple projects with different IDs, when I call `GET /api/v1/projects?q=<id-fragment>`, then the response includes only projects whose `id`, `title`, or `product_description` contains that keyword (case-insensitive).
2. Given I own multiple projects in dashboard view, when I call `GET /api/v1/dashboard/summary?q=<id-fragment>`, then dashboard cards are filtered by the same `id`/`title`/`product_description` keyword behavior.
3. Given status filters are also provided, when I call `GET /api/v1/projects` or `GET /api/v1/dashboard/summary` with both `status` and `q`, then results satisfy both filters together and do not return projects outside the selected statuses.
