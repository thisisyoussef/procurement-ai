# US: Dashboard Contacts Minimum Query Length Guardrail

As a procurement manager
I want dashboard contact search to reject one-character keyword queries
So that supplier search results remain relevant and performant

## Acceptance Criteria

### Scenario 1: Reject one-character contact query
Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?q=a`
Then the API responds with `422 Unprocessable Entity`
And the response detail states the query must be at least 2 characters

### Scenario 2: Accept two-character contact query
Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?q=ac`
Then the API responds with `200 OK`
And the contacts service receives `contact_query="ac"`

### Scenario 3: Keep whitespace-only query behavior
Given I am authenticated
When I request `GET /api/v1/dashboard/contacts?q=%20%20%20`
Then the API responds with `200 OK`
And the contacts service receives `contact_query=None`
