As a returning procurement user
I want dashboard contact search to support multi-term queries
So that I can quickly find suppliers using combined clues like name, location, and phone fragments.

Acceptance criteria

Given I am authenticated and call `GET /api/v1/dashboard/contacts?q=acme%20detroit`
When one contact has `name=Acme Precision Metals` and `city=Detroit`
Then the contact is returned because all query terms match across searchable contact fields.

Given I am authenticated and call `GET /api/v1/dashboard/contacts?q=acme%203125550142`
When one contact has `name=Acme Precision Metals` and `phone=+1 (312) 555-0142`
Then the contact is returned because terms can match across text and digit-normalized phone values.

Given I am authenticated and call `GET /api/v1/dashboard/contacts?q=acme%20toronto`
When no contact satisfies every term
Then the response excludes partial matches and returns only contacts matching all provided terms.
