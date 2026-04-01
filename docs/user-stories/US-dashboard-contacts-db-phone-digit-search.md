# User Story: Dashboard Contacts DB Phone Digit Search

As a procurement manager
I want digit-only phone queries on dashboard contacts to match formatted phone numbers in all contact sources
So that I can quickly find suppliers by phone regardless of how numbers are stored

## Acceptance Criteria

### Scenario 1: Digit-only query matches DB-backed formatted phone numbers
Given supplier contacts are persisted in the database with formatted phone numbers like `+1 (312) 555-0142`
When I request `GET /api/v1/dashboard/contacts?q=3125550142`
Then the response includes the matching supplier contact
And non-matching contacts are excluded

### Scenario 2: Phone-digit filtering runs before response limiting
Given there are multiple DB-backed contacts and only one matches digit query `3125550142`
When I request `GET /api/v1/dashboard/contacts?limit=1&q=3125550142`
Then the single returned contact is the matching supplier
And the match is not dropped by pre-filter limit truncation

### Scenario 3: Text keyword queries keep existing repository filtering behavior
Given I search dashboard contacts by text keyword like `acme`
When I request `GET /api/v1/dashboard/contacts?q=acme`
Then repository query filtering remains enabled for text search
And response shape and status codes remain unchanged
