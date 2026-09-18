# Code Generator Implementation Phases

This page describes the implementation phases of the SAS to PySpark code generator. The generator consumes semantic ETL IR and produces deterministic PySpark DataFrame API modules with diagnostics and provenance.

## Implementation phases

### Phase 1: Generator scaffold
1. Create the `sas_generator` package and public `generate_job` entry point
2. Define generated-artifact, configuration, and generation-diagnostic models
3. Validate required `Job`, source, target, and expression fields before emission
4. Emit a deterministic module skeleton with imports and `run_job` function
5. Add compilation and golden-source snapshot test helpers

### Phase 2: Naming and runtime contract
1. Define the `run_job(spark, sources, runtime=None)` input/output contract
2. Resolve source references from the supplied DataFrame mapping
3. Generate stable Python identifiers for SAS dataset names and aliases
4. Handle identifier collisions and reserved names deterministically
5. Report missing, unresolved, and macro-generated dataset references as diagnostics

### Phase 3: Expression generation
1. Generate typed literals and column references as PySpark `Column` expressions
2. Support arithmetic, comparison, and logical expression nodes
3. Add a narrowly scoped compatibility translator for current simple raw expressions
4. Add a SAS-to-PySpark registry for supported functions
5. Produce structured diagnostics for unsupported functions and ambiguous semantics

### Phase 4: Data-step generation
1. Emit source resolution, filters, and assignments as a DataFrame pipeline
2. Emit KEEP, DROP, and RENAME once their semantic IR nodes are available
3. Bind data-step output dataset names to generated DataFrames
4. Preserve transform ordering using an ordered IR operation list
5. Add Spark behavioral tests for simple DI Studio-style data steps

### Phase 5: PROC SQL generation
1. Emit source aliases, joins, filters, and projections with the DataFrame API
2. Emit group-by and aggregate operations from structured aggregate expressions
3. Bind CREATE TABLE AS SELECT targets to generated output DataFrames
4. Add support for UNION after the IR represents set operations
5. Diagnose unsupported INSERT, UPDATE, and DELETE operations pending a storage contract

### Phase 6: Diagnostics, provenance, and validation
1. Attach IR and SAS source provenance to generator diagnostics
2. Emit concise source-location comments around top-level generated transforms
3. Add strict and permissive partial-generation modes
4. Compile every generated module in tests
5. Add parse-to-lower-to-generate regression tests for representative DI Studio jobs

### Phase 7: Runtime adapters and production hardening
1. Add optional adapters for catalog, Parquet, Delta, JDBC, and Hive I/O
2. Define explicit output persistence behavior and write modes
3. Expand the SAS function and type-compatibility registry based on regression samples
4. Add deterministic formatting and source-map output
5. Document deployment configuration, unsupported constructs, and migration review workflow