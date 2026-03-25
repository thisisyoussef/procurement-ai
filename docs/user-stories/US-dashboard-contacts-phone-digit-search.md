As a procurement manager reviewing supplier contacts
I want to search contacts with digit-only phone input
So that I can find suppliers quickly even when phone numbers are formatted differently.

Acceptance criteria

Given a supplier contact phone is stored as `+1 (312) 555-0142`
When I call `GET /api/v1/dashboard/contacts?q=3125550142`
Then the supplier is returned in the filtered contacts response.

Given a supplier contact phone is stored with punctuation and spaces
When I search with a partial digit sequence like `5550142`
Then the supplier is matched and returned.

Given no supplier phone contains the digit sequence `9999999`
When I call `GET /api/v1/dashboard/contacts?q=9999999`
Then no suppliers are returned from phone matching for that query.
