# US: Dashboard Contacts Phone Digit Search

As a returning procurement user
I want dashboard contact search to match phone numbers even when I type digits only
So that I can quickly find suppliers without re-entering formatting characters

## Acceptance Criteria

### Scenario 1: Digits-only query matches formatted phone values
Given I am authenticated and a supplier contact has phone `+1 (312) 555-0142`
When I request `GET /api/v1/dashboard/contacts?q=3125550142`
Then the supplier is returned in the contacts response

### Scenario 2: Existing keyword matching behavior remains intact
Given I am authenticated and supplier contacts include names, emails, and locations
When I request `GET /api/v1/dashboard/contacts?q=acme`
Then matching suppliers are still returned using existing case-insensitive keyword filtering

### Scenario 3: Non-matching phone digits do not produce false positives
Given I am authenticated and supplier contacts do not include the queried phone digits
When I request `GET /api/v1/dashboard/contacts?q=9999999999`
Then the contacts response excludes those suppliers
