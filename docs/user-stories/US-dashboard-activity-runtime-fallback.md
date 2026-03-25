As a returning procurement user
I want dashboard activity to still load when DB activity events are unavailable
So that I can continue tracking project progress from recent timeline updates.

Acceptance criteria

Given the activity events table returns no rows for my account
When I request `GET /api/v1/dashboard/activity`
Then the API returns timeline events from my projects ordered newest first.

Given timeline events exist for multiple users
When I request `GET /api/v1/dashboard/activity` as an authenticated user
Then only events from my own projects are included.

Given I request `GET /api/v1/dashboard/activity?cursor=<timestamp>`
When runtime timeline fallback is used
Then only events older than the cursor are returned and `next_cursor` matches the last event timestamp in the page.
