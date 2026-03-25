As a procurement operator
I want dashboard contact search to reject 1-character queries
So that results stay relevant and the contacts panel avoids noisy broad matches

Acceptance criteria

1. Given I am on the dashboard contacts view
When I request `GET /api/v1/dashboard/contacts?q=a`
Then the API responds with `422` and detail `Query must be at least 2 characters.`

2. Given I search with surrounding whitespace
When I request `GET /api/v1/dashboard/contacts?q=%20acme%20`
Then the API trims the query and forwards `acme` to contacts lookup

3. Given I search with whitespace only
When I request `GET /api/v1/dashboard/contacts?q=%20%20%20`
Then the API treats the query as empty and returns contacts without a keyword filter
