## User Story: Safe Clarifying Answer Errors

As a signed-in procurement manager
I want clarifying-answer submission failures to return a safe, consistent error message
So that I can retry confidently without seeing internal system details

## Acceptance Criteria

### Case 1: Successful answer submission resumes the pipeline
Given my project is waiting for clarifying answers
When I call `POST /api/v1/projects/{id}/answer` with valid answers
Then the API returns `200` with `status = "resumed"`
And the project transitions to `discovering`.

### Case 2: Unexpected answer-processing errors are sanitized
Given my project is waiting for clarifying answers and answer processing hits an unexpected server exception
When I call `POST /api/v1/projects/{id}/answer`
Then the API returns `500` with `detail = "Failed to process answers. Please try again."`
And the response does not include raw exception strings or tracebacks.

### Case 3: Clarifying-state guard remains strict
Given my project is not in `clarifying` status
When I call `POST /api/v1/projects/{id}/answer`
Then the API returns `400` with `detail = "Project is not waiting for answers"`.
