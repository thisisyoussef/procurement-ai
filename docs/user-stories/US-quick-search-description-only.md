As a procurement manager
I want quick search to work with only my product description
So that I can run a fast supplier search without creating a full project first

## Acceptance Criteria

1. Given I am authenticated and provide a valid `product_description`, when I call `POST /api/v1/projects/search` without a `title`, then the API returns `200` with quick-search results.
2. Given I send a whitespace-only `product_description`, when I call `POST /api/v1/projects/search`, then the API returns `422` validation error.
3. Given an unexpected internal exception occurs while running quick search, when I call `POST /api/v1/projects/search`, then the API returns `500` with detail `Failed to run quick search. Please try again.` and does not expose raw exception details.
