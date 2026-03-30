# User Story: Dashboard Start Uses Description Preview for Blank Title

As a procurement manager
I want dashboard quick-start projects to auto-name from my brief when my custom title is blank
So that I can recognize projects immediately instead of seeing a generic fallback name

## Acceptance Criteria

1. Given I provide a custom title with surrounding spaces, when I start a dashboard project, then the project title is saved as the trimmed custom title.
2. Given I provide a custom title that is whitespace-only, when I start a dashboard project, then the project title falls back to the first 80 characters of the trimmed description.
3. Given I omit the custom title, when I start a dashboard project, then the project title uses the first 80 characters of the trimmed description.
