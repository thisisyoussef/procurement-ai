As a dashboard user
I want dashboard project start source values to be normalized to supported entries
So that redirect attribution and analytics remain consistent and reliable.

Acceptance criteria

Given I submit `POST /api/v1/dashboard/projects/start` with `source="dashboard_search"`
When the project is created successfully
Then the response `redirect_path` includes `entry=dashboard_search`.

Given I submit `POST /api/v1/dashboard/projects/start` with whitespace/case variants like `source="  DASHBOARD_SEARCH  "`
When the endpoint normalizes source input
Then the response `redirect_path` includes `entry=dashboard_search`.

Given I submit `POST /api/v1/dashboard/projects/start` with an unsupported source like `source="dashboard_sidebar"`
When the endpoint validates and normalizes source input
Then the response `redirect_path` includes the safe default `entry=dashboard_new`.
