As a returning procurement user
I want to search supplier contacts on the dashboard
So that I can quickly find the right supplier and reopen the related project.

Acceptance criteria

Given I am authenticated and open `GET /api/v1/dashboard/contacts?q=acme`
When supplier contacts include mixed names and emails
Then only contacts matching the keyword (case-insensitive) are returned.

Given I pass whitespace-only query text to `GET /api/v1/dashboard/contacts?q=%20%20%20`
When the endpoint normalizes query input
Then the query is treated as empty and returns the unfiltered contact list.

Given I open the dashboard Contacts tab and enter a supplier/location keyword
When I apply the filter
Then the URL keeps `contacts_q=<term>` and the contacts list refreshes using that filter.
