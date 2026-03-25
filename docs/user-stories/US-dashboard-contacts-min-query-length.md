As a procurement manager reviewing supplier contacts
I want dashboard contacts search to require at least 2 characters
So that short accidental queries do not return noisy broad results.

Acceptance criteria

Given I call `GET /api/v1/dashboard/contacts?q=a`
When the request query contains one non-whitespace character
Then the API returns `422` with `Query must be at least 2 characters.`

Given I call `GET /api/v1/dashboard/contacts?q=ab`
When the request query contains two characters
Then the API accepts the request and applies the query filter.

Given I call `GET /api/v1/dashboard/contacts?q=%20%20%20`
When the query is whitespace-only
Then the API treats it as no query and returns the unfiltered contacts behavior.
