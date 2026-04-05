## User Story: Requirements Parser Category Grounding

As a sourcing manager
I want the requirements parser to reject model-invented product categories that do not match my request
So that supplier discovery stays focused on the actual part I need sourced

## Acceptance Criteria

### Case 1: Mismatched category is rebuilt from user input
Given my request asks for injection molded ABS enclosures
When the model returns `product_type` and search queries for tote bags
Then the parser rebuilds `product_type` from my request and removes tote-related search queries.

### Case 2: Grounded category is preserved
Given my request asks for custom tote bags
When the model returns a tote-bag `product_type` and tote-bag search queries
Then the parser preserves the model `product_type` and search queries.

### Case 3: Rebuilt queries stay B2B-focused
Given my request asks for CNC machined aluminum brackets
When the model returns a mismatched retail-style category and queries
Then rebuilt search queries are generated from the request and include B2B manufacturer/supplier intent.
