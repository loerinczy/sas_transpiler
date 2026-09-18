# PySpark Code Generator Design

This document describes the design of the code generator that emits PySpark code from the semantic ETL IR.

## High-level pipeline
- Semantic ETL IR ingestion
- IR validation and capability analysis
- Naming and dependency planning
- Expression translation
- Transform emission
- Runtime scaffolding emission
- Formatting and source provenance generation
- Generated-code validation and test snapshots

The generator consumes semantic IR only. It must not reparse SAS source or depend on the syntax IR except through provenance metadata already attached during parsing and lowering.

## Package/module layout
The code generator should be organized around clear responsibilities:

```
sas_generator/
    __init__.py
    generator.py
    models.py
    validation.py
    naming.py
    expressions.py
    data_step_emitter.py
    sql_emitter.py
    runtime.py
    formatting.py
    diagnostics.py
```

This separation keeps IR validation, language translation, and generated-code formatting independently testable. Initially, generator models may reuse `sas_parser.models`; a generator-local model layer should only be added when it represents generator-specific concepts such as generated artifacts or runtime configuration.

## Generator contract

### Input
The generator accepts a `Job` from the semantic ETL IR. Current core fields are:
- `name`
- `inputs` as `SourceRef`
- `outputs` as `TargetRef`
- `transforms` as `Assignment`
- `filters` as `Filter`
- `joins` as `Join`
- `aggregates` as `Aggregate`

Expressions may be represented by `ColumnRef`, `Literal`, `FunctionCall`, or later expression-tree nodes. During the first implementation, string-bearing `Literal` expressions produced by the current lowerer should be supported through a clearly isolated compatibility translator.

### Output
The generator returns a `GeneratedModule`-like artifact containing:
- Python source text
- Required imports
- Generated dataset bindings and output bindings
- Diagnostics
- Source-to-generated provenance entries where available

The primary artifact is a standalone PySpark module exposing a function such as `run_job(spark, sources, runtime=None)`. The function returns a mapping of output dataset names to DataFrames. File reads and writes are deliberately outside the initial contract because SAS libref mappings and deployment-specific storage configuration cannot be inferred safely from the IR alone.

### Determinism
Equivalent canonical IR must produce byte-stable generated code. Imports, dataset bindings, transform order, and diagnostics must be emitted in a deterministic order.

## Uncertainties cleared
- Does the generator receive parsed SAS syntax directly?
  Answer: No. It consumes semantic ETL IR. Parser and lowerer changes must preserve enough semantic detail and source provenance for code generation.
- Does the first generator implement complete SAS runtime behavior?
  Answer: No. The initial scope targets DI Studio ETL data flow represented in the IR. Unsupported or unresolved behavior must become explicit diagnostics, never silently altered PySpark code.
- How are source datasets supplied?
  Answer: Callers provide a mapping of SAS dataset references to DataFrames. Runtime adapters for catalog, file, or JDBC reads may be added later.
- How are output datasets materialized?
  Answer: The first version returns output DataFrames. Persistence is an explicit later runtime concern.
- Is generated SQL preferred over DataFrame API calls?
  Answer: Emit the PySpark DataFrame API for semantic transforms. This keeps output independent of temporary SQL views and maps cleanly to the ETL IR.

## Naming and dataset resolution

SAS dataset names can include librefs, periods, macro references, and characters unsuitable for Python identifiers. The naming layer must:
- Preserve the original dataset reference as the lookup key and output key
- Create stable, readable Python variable names such as `df_work_stage`
- Sanitize invalid identifier characters
- Resolve collisions with deterministic suffixes
- Reserve names used by the runtime API, imports, and generated helper variables
- Diagnose unresolved dynamic names, including macro-generated references

Dataset aliases used in joins must remain distinct from physical dataset references. The generator should retain an internal relation binding table so later operations are applied to the intended DataFrame.

## Expression translation

Translate semantic expressions into PySpark `Column` expressions:
- `ColumnRef(name)` becomes `F.col(name)` or an alias-qualified column reference
- `Literal(value)` becomes `F.lit(value)` when it is a typed literal
- Arithmetic becomes PySpark column arithmetic
- Comparisons become boolean column expressions
- Logical operations become `&`, `|`, and `~` with explicit parentheses
- String concatenation becomes `F.concat` or `F.concat_ws` according to IR semantics
- `FunctionCall` maps through a supported SAS-to-PySpark function registry
- CASE expressions become chained `F.when(...).when(...).otherwise(...)`

SAS and Spark differ in missing values, type coercion, string comparison, date/time functions, and null handling. The generator must implement a documented mapping only when semantics are known. Otherwise, it must report `UnsupportedConstruct` or `AmbiguousConstruct` and omit the affected executable operation rather than guessing.

The compatibility translator for raw expression strings is transitional. It should handle only parser-supported simple arithmetic, comparisons, logical operators, literals, and column references. It must not use string substitution as the long-term expression implementation.

## Data-step transform emission

The data-step emitter translates ordered semantic operations into a DataFrame pipeline:
- `SourceRef` resolves a supplied input DataFrame
- `Filter` becomes `.filter(translated_condition)`
- `Assignment` becomes `.withColumn(target, translated_expression)`
- KEEP becomes `.select(...)`
- DROP becomes `.drop(...)`
- RENAME becomes `.withColumnRenamed(...)`
- Output targets become named returned DataFrames

Ordering is significant. Filters and assignments must be emitted in semantic execution order. The current `Job` groups transforms by type, which cannot preserve all SAS data-step ordering. Before supporting interleaved transforms, evolve the IR with an ordered operation list rather than reconstructing order from separate lists.

Multiple input datasets, `MERGE`, `UPDATE`, `RETAIN`, arrays, and conditional output routing require dedicated semantic IR before emission. The generator should diagnose these cases until their IR representation exists.

## SQL transform emission

The SQL emitter translates semantic query operations with the DataFrame API:
- Source references become DataFrame bindings and aliases
- Joins become `.join(right, condition, join_type)`
- Filters become `.filter(condition)`
- Projections become `.select(...)`
- Aggregations become `.groupBy(...).agg(...)`
- CREATE TABLE AS SELECT produces an output dataset binding
- UNION becomes `unionByName` once represented in the IR

The emitter must preserve SQL clause order and alias scope. Aggregates require explicit expression nodes, aliases, and non-aggregate projection metadata; `Aggregate.measures` strings are sufficient only for the initial supported subset and should be replaced by structured aggregate expressions.

`INSERT`, `UPDATE`, and `DELETE` are not DataFrame transformations with uniform Spark semantics. They require an explicit target-storage strategy and are unsupported in the first code generator unless a later IR extension specifies the intended behavior.

## Macro and DI Studio scaffolding

Macros and DI Studio scaffolding are parser concerns until they affect executable ETL semantics. Generator behavior is:
- Use statically resolved macro values already reflected in the semantic IR
- Preserve unresolved macro references in diagnostics and provenance
- Accept runtime parameters only through an explicit runtime configuration interface
- Do not emit SAS macro syntax, `%include`, `%let`, or DI orchestration boilerplate as Python code
- Optionally preserve relevant source text as generated comments only when it aids debugging and does not change execution

Job dependencies should be represented as required source keys in the generated function contract. Other-job scheduling remains an orchestration concern outside this generator.

## Diagnostics and provenance

The generator must be resilient and must produce diagnostics instead of failing at the first unsupported node.

Required diagnostic categories:
- `UnsupportedConstruct`
- `AmbiguousConstruct`
- `MissingDependency`
- `InvalidIR`
- `ExpressionTranslationError`
- `NameResolutionError`
- `RuntimeConfigurationRequired`

Each diagnostic should include a message, severity, the IR node or dataset involved, and any available SAS source span/text. Generated code should contain concise provenance comments around top-level transforms when source spans are available. A diagnostic with error severity prevents executable output unless a permissive partial-generation mode is explicitly selected.

## Error handling and resilience

The generator should:
- Validate the IR before generating code
- Continue collecting independent diagnostics where safe
- Never silently skip a supported transform
- Never fabricate semantics for unsupported SAS behavior
- Produce partial source only when clearly marked non-executable or when callers request it
- Raise a structured generation exception only for invalid invocation or strict-mode errors

## Testing strategy

Tests should be layered and snapshot-based where useful:
- Unit tests for naming, expression mapping, diagnostics, and formatting
- Emitter tests for individual data-step and SQL IR fragments
- Golden-source tests for canonical `Job` inputs and exact generated Python output
- Compilation tests using `compile()` for every generated module
- Behavioral tests using a local Spark session for supported transformations
- Regression tests that parse, lower, generate, and execute representative DI Studio job samples

Generated code must be tested for deterministic output, valid Python syntax, expected DataFrame behavior, and useful diagnostics for unsupported constructs.

## Future extensions
- Runtime adapters for catalog, Parquet, Delta, JDBC, and Hive table I/O
- Structured conditional, projection, rename, retain, and output-routing operations
- Broader SAS function registry and type/date compatibility rules
- SQL set operations and data-modification semantics backed by a storage contract
- Source maps that link generated lines to SAS source spans
- Configurable code style and module packaging