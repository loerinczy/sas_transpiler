This document describes the design of the parser.

## High-level pipeline
- File ingestion
- Preprocessing and normalization
- Structural segmentation
- Statement tokenization
- Block-aware parsing
- Construct-specific parsing
- Semantic lowering into ETL IR
- Diagnostics generation
- Validation and test snapshots



## Package/module layout
The parser should be organized around clear responsibilities:

sas_parser/
- init.py
- models.py
- lexer.py
- parser.py
- blocks.py
- data_step_parser.py
- sql_parser.py
- macro_parser.py
- semantic_lowerer.py
- diagnostics.py
- utils.py

This separation keeps the parser maintainable and allows incremental implementation.


## Uncertainties cleared
- Are we parsing one job file at a time or multiple jobs plus dependencies?
   Answer: One job file at a time, but the transpiler should be aware of dependencies on external data sources and other jobs for accurate transpilation.


## Detailed parser implementation steps
### Step 1: File ingestion and normalization
Read the SAS file as text and normalize:
- Preserve line numbers and offsets
- Keep raw text for fallback extraction
- Normalize line endings
- Remove or flag encoding issues
- Record file metadata

This stage should not change logic, only ensure parsing has stable input.

### Step 2: Structural segmentation
Identify top-level regions:
- PROC SQL blocks
- DATA step blocks
- Macro definitions
- DI Studio scaffolding
- Comments and metadata sections
- Unrecognized sections

This stage should produce a lightweight syntax tree with partitions at the top level.

Important idea:
Do not parse everything deeply at once. First split the job into large logical units. This reduces ambiguity and helps separate DI Studio boilerplate from actual ETL logic.

### Step 3: Lexical analysis
Build a tokenizer for SAS syntax that understands:
- Keywords: DATA, PROC, RUN, SQL, SET, MERGE, UPDATE, WHERE, BY, IF, THEN, ELSE, INPUT, PUT, OUTPUT, KEEP, DROP, RENAME
- Operators: =, +, -, *, /, ||, >, <, >=, <=, ~=, in, not in
- Delimiters: ;, (, ), comma, period, colon
- String literals
- Macro tokens: %, &

The lexer should also track:
- Position
- Line
- Column
- Token type
This is critical because SAS syntax is forgiving and often contains punctuation-heavy expressions.

### Step 4: Statement parsing
Parse statements in order and create AST-like nodes:

- Assignment statement
- If statement
- Do/End block
- Set statement
- Merge statement
- Where clause
- Keep/Drop section
- Return/Output statement
- Procedure invocation
- SQL statement
The parser should parse by statement boundary, not by line alone, because one logical statement may span multiple lines.

### Step 5: Data step parsing
This is the most important part of the parser for ETL jobs.

Parse and model:
- DATA statement
- SET / MERGE / UPDATE / DELETE patterns
- Array declarations
- Variable assignments
- Conditional branches
- Retain logic
- Keep/drop/rename lists
- Output dataset changes
- Derived variables

Represent these in syntax nodes first, then lower to semantic ETL IR.

Example semantic lowering:

DATA step assignment like x = a + b; becomes AssignmentNode
IF condition then ...; becomes FilterNode or ConditionalNode
SET table; becomes SourceRef + DataFrame/Relation node
KEEP var1 var2; becomes projection specification

### Step 6: PROC SQL parsing
Parse SQL blocks with support for:
- SELECT
- FROM
- WHERE
- GROUP BY
- ORDER BY
- JOIN
- UNION
- CASE WHEN
- CREATE TABLE AS SELECT
- INSERT INTO
- UPDATE
- DELETE

The parser should treat this as data-flow oriented:

- FROM clauses become source references
- SELECT and expression list become projected columns
- WHERE becomes filter
- JOIN becomes join node
- GROUP BY and aggregate functions become aggregation nodes
- CREATE TABLE AS SELECT becomes target dataset specification

This is the closest match to PySpark semantics.

### Step 7: Macro and DI-specific scaffolding handling
DI Studio jobs often contain macro wrappers and generated scaffolding around real logic. The parser must not overly fail here.

Recommended approach:

Parse macros as container nodes with raw body preserved
Extract only the content that looks like actual data logic
Preserve macro references as metadata or unresolved nodes
Treat unknown DI scaffolding as metadata rather than disruptive syntax
This avoids brittle failures when macros are present but irrelevant to target ETL logic.

### Step 8: Semantic lowering
Lower AST/syntax nodes into ETL IR:

- Data step statements become transform steps
- SQL statements become SQL transform nodes
- Table references become dataset nodes
- Column expressions become expression trees

This layer should be deterministic and easy to inspect.

### Step 9: Unresolved and unsupported detection
The parser should explicitly mark:
- Unsupported SAS functions
- Ambiguous syntax
- Macro-generated logic that cannot be resolved statically
- Dynamic references
- External environment assumptions

This is essential because you do not want hidden failure at code generation time.

### Step 10: Diagnostics and provenance
Attach metadata to each node:

- Source text
- Line/column range
- Confidence level
- Warnings
- Unsupported reasons
This will later help code generation and debugging.


## Parsing strategy by construct type
### Data step parsing
Focus on:
- SET statements
- WHERE conditions
- IF/ELSE branching
- assignment expressions
- outputs and retain behavior
- keep/drop

Pattern:
- Parse statement by statement
- Lift into transform graph
- Preserve ordering

### PROC SQL parsing
Focus on:
- SELECT list
- FROM / JOIN
- WHERE / HAVING
- GROUP BY / aggregate functions
- CREATE TABLE AS SELECT
- Insert/update/delete as edge cases

Pattern:
- Parse table and column references early
- Build expression tree for SELECT and WHERE
- Keep SQL semantics in semantic IR rather than raw txt

### Macro parsing
Focus on:
- Macro declarations
- Parameter binds
- Macro variable use
- Raw body retention
- Detecting whether a macro body contains actual ETL logic

Pattern:
- Parse macros as blocks with extracted metadata instead of full semantics


## Error-handling and resilience
The parser should never fail catastrophically on a single unsupported construct.

### Required behavior
- Continue parsing around unsupported blocks
- Record diagnostics
- Preserve raw text in the node
- Flag low-confidence regions

### Recommended categories
- SyntaxWarning
- SyntaxError
- UnsupportedConstruct
- AmbiguousConstruct
- MissingDependency

This makes validation easier and helps the code generator handle partial success gracefully.