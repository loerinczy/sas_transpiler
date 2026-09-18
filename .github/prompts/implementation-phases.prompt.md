This page describes the implementation phases of the SAS to PySpark transpiler, focusing on IR generation and parser implementation currently.


## Implementation phases
### Phase 1: Core scaffold
1. Define IR schema
2. Define AST node classes
3. Build file ingestion and section splitter
4. Build lexer and token model
5. Add diagnostics framework

### Phase 2: Statement-level parser
1. Parse assignment statements
2. Parse simple IF/ELSE blocks
3. Parse basic SQL clauses
4. Add statement ordering and metadata

### Phase 3: Data step support
1. Parse SET, WHERE, KEEP, DROP, RENAME
2. Parse assignment expressions
3. Model simple DataStep transformation logic
4. Add debug snapshots

### Phase 4: PROC SQL support
1. Parse query blocks
2. Parse joins, filters, projections, aggregates
3. Model CREATE TABLE AS SELECT and common ETL patterns

### Phase 5: Macro and DI-specific handling
1. Recognize wrapper blocks and metadata
2. Preserve non-ETL scaffolding
3. Reduce parse failure risk from job boilerplate

### Phase 6: Semantic lowerer and validation
1. Lower syntax nodes to ETL IR
2. Add canonicalization rules
3. Run regression tests against sample DI jobs


