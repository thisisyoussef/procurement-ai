## User Story: DB-Backed Contact Phone Digit Search

As a procurement manager reviewing supplier contacts
I want digit-only phone queries to match DB-backed contact phone values
So that I can reliably find suppliers even when stored phone formats include punctuation or spaces.

## Acceptance Criteria

### Case 1: Full-digit query matches formatted DB phone
Given a supplier contact is stored in DB with phone `+1 (312) 555-0142`
When I request `GET /api/v1/dashboard/contacts?q=3125550142`
Then the supplier is returned.

### Case 2: Partial-digit query matches formatted DB phone
Given a supplier contact is stored in DB with phone `+1 (312) 555-0142`
When I request `GET /api/v1/dashboard/contacts?q=5550142`
Then the supplier is returned.

### Case 3: Non-matching digit query returns no phone-based DB matches
Given DB-backed contacts have no phone containing `9999999`
When I request `GET /api/v1/dashboard/contacts?q=9999999`
Then no suppliers are returned from DB phone matching for that query.
