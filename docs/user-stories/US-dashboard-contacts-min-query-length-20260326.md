# User Story: Dashboard Contacts Minimum Query Length

## Story
As a procurement manager
I want supplier contacts search to require a meaningful query
So that I get relevant matches and avoid noisy broad results

## Acceptance Criteria
1. Given an authenticated user calls `GET /api/v1/dashboard/contacts` with `q` containing only one non-whitespace character
   When the API validates request parameters
   Then it returns `422` with `"Contact query must be at least 2 characters."`

2. Given an authenticated user calls `GET /api/v1/dashboard/contacts` with `q` containing two or more non-whitespace characters
   When the dashboard contacts endpoint processes the request
   Then it returns `200` and forwards the trimmed query to the contacts service

3. Given a user is on the dashboard Contacts tab and enters a one-character query in the filter input
   When they apply the filter
   Then the UI keeps the existing results, shows an inline validation message, and does not persist the short query into `contacts_q`

## Notes
- This change is intentionally narrow and does not alter contacts ranking, deduplication, or pagination.
- Empty/whitespace-only query values still clear the filter and load unfiltered contacts.
