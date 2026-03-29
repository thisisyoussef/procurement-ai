# User Story: Dashboard Contacts Project-Context Search

## Story
As a procurement manager  
I want to search supplier contacts by the project context they are tied to  
So that I can quickly find the right supplier when I remember the project first, not the supplier name.

## Acceptance Criteria
1. Given I have supplier contacts linked to projects with titles and descriptions, when I query dashboard contacts with a project-title keyword, then suppliers linked to matching projects are returned even if the supplier fields do not contain that keyword.
2. Given a multi-term query, when one term matches project context and another matches supplier contact fields, then only contacts satisfying all terms are returned.
3. Given a query with non-matching project context terms, when I call dashboard contacts, then non-matching suppliers are excluded.

## Notes
- This story extends existing contacts keyword filtering and keeps current status-filter and result-limit behavior.
- Matching remains case-insensitive and continues to support phone digit matching.
