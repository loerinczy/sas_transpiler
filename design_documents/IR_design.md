This document describes the design of the IR representation.

## The proposed two-layer IR design
### Layer 1: Syntax IR
A parsed structural representation of the SAS file:
- Program
- Section
- Statement
- Block
- Procedure
- Macro block
- Data step
- SQL block
- Metadata block
This layer captures the file structure and preserves the original order.

### Layer 2: Semantic ETL IR
A normalized representation focused on data movement and transformation:
- Job
- Dataset
- Column
- Transform
- Assignment
- Filter
- Join
- Aggregation
- DerivedColumn
- SourceRef
- TargetRef
- ProcedureCall
- UnsupportedConstruct
This layer is what the code generator consumes.

Why this is good:

It allows the parser to be structurally faithful without making the generator depend on SAS syntax details.
It supports later adaptation to PySpark rules and edge cases.
It makes unsupported constructs explicit instead of silently discarding them.

## Core AST/IR nodes
- Program
- Section
- Statement
- DataStep
- ProcSql
- MacroBlock
- SourceRef
- TargetRef
- Assignment
- Filter
- Join
- Aggregate
- Project
- Dataset
- ColumnRef
- Literal
- FunctionCall
- UnsupportedNode
- Diagnostic
- Minimal expression model

Expressions should support:
- Arithmetic
- Comparison
- Logical operations
- String concatenation
- CASE
- Function calls
- Column references
- Literals
- Parenthesized expressions

This provides the minimal functionality needed to generate PySpark expressions later.

## Uncertainties cleared
- Question: What exact SAS constructs are guaranteed to appear in the generated DI Studio jobs?
   Answer: Data step, PROC SQL and Macros, call symputs, %include, %let, automatic variables. Everything that DI Studio might generate. It is fine to focus first on Data step, PROC SQL and Macros, and extend to other constructs as needed.
- Are we expected to support comments, nested parentheses, quoted strings, and multiline expressions accurately?
   Answer: Yes, the parser should handle these accurately to ensure correct parsing of the SAS jobs.
- How should unsupported constructs be represented?
   Answer: Unsupported constructs should be represented in the IR in a way that clearly indicates they are not supported, but still allows the rest of the job to be accurately transpiled. The raw content of the unsupported constructs should be preserved in the IR for reference.
- Are there naming conventions for temporary variables, output tables, and work datasets that we must model?
   Answer: No, there are no strict naming conventions that must be modeled, but the transpiler should be aware of common patterns used in DI Studio-generated jobs.
- Do we need to maintain source spans for debugging and later code generation?
   Answer: Yes, maintaining source spans is important for accurate debugging.