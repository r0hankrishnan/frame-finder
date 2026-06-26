# Frame Finder Project Plan

## What is this project (high-level)?

Frame Finder is a tool that lets tennis players search for tennis racquets by describing what they are looking for in natural language. For the MVP, it will be a search bar that takes a NL query from a user.
After the user enters a query, code in the background will parse the query into a semantic query, a list of lexical keywords to try and match, and "hard" constraints that could be filtered from structured data into a JSON object.
Then, from the returned JSON object, the code runs a semantic search on teh semantic text, a lexical search over the keywords, and runs a specialized set of functions to apply structured filters if extracted. After doing all three, the code combines each score for each racquet into one weighted score and then uses argmax to return the indices in order for highest to lowest scores (or sort and return sorted data object directly). Then that sorted data object can be fetched by an API and displayed on a simple front end by unpacking it with JS. 

## What are the actual steps that the code needs to do?
[ ] Accept user query
[ ] Pass query to LLM with prompt
[ ] Handle + validate structured JSON response and have acceptable fallbacks
[ ] 


## To do
[x] Create LLM Adapters
[x] Create distill.py
[x] Create distillation script
[x] Run distillation
[x] Validate distilled descriptions
[ ] Create parse_query.py
    [ ] Create pydantic model
    [ ] Create orchestration function
        [ ] Retry logic
        [ ] Output validation logic
        [ ] Fall back value

**How are you handling racquets with empty descriptions?**
- They don't break the embedder so let them be embedded with an empty vector and then if they still
have strong matches via BM25 they could surface.