# User Story: Dashboard summary search by project ID

As a procurement user  
I want dashboard summary search to match project IDs  
So that I can quickly find a specific project from links, notes, and support messages.

## Acceptance Criteria

### 1. Match by project ID keyword
Given I have dashboard projects with different IDs  
When I call `GET /api/v1/dashboard/summary?q=abc123`  
Then only projects whose ID contains `abc123` (case-insensitive) are returned.

### 2. Preserve case-insensitive behavior
Given a project ID contains mixed-case letters  
When I search using a different case in `q`  
Then the matching project is still returned.

### 3. Combine with status filters
Given matching project IDs exist across multiple statuses  
When I call `GET /api/v1/dashboard/summary?status=discovering&q=abc123`  
Then only projects that satisfy both the status filter and the project ID filter are returned.
