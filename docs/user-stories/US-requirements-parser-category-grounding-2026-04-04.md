As a sourcing manager
I want requirements parsing to stay grounded in my actual product request
So that supplier discovery targets the correct manufacturing category

Acceptance Criteria

1. Given the user asks for "injection molded ABS enclosures" and the model returns `product_type: tote bag`
When requirements are parsed
Then the parser rebuilds `product_type` from raw user input and generated `search_queries` contain no tote-bag terms.

2. Given the user asks for tote bags and the model returns `product_type: tote bag`
When requirements are parsed
Then the parser keeps the grounded product category and preserves tote-focused supplier queries.

3. Given the user asks for CNC machined aluminum brackets and the model returns a mismatched category with empty `search_queries`
When requirements are parsed
Then the parser regenerates default B2B manufacturer/factory queries from the rebuilt product type.
