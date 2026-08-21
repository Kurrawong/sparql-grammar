# Migrating from sparql-grammar-pydantic

Most call sites are unchanged — `Var(value="x")`, `IRI(value="...")`,
`TriplesSameSubjectPath.from_spo(...)`, `Expression.from_primary_expression(...)`,
`TriplesBlock.from_tssp_list(...)` and `GroupGraphPatternSub.add_pattern(...)` all still
work. The differences worth knowing:

| Before | Now | Why |
|---|---|---|
| `GraphTerm(content=x)` | pass `x` directly | SPARQL 1.2 removed `GraphTerm` |
| `VarOrTerm(varorterm=x)` | pass `x` directly | alternation productions are union aliases |
| `PrimaryExpression(content=x)` | pass `x` directly | same |
| `from_tssp_list` reversed its input | keeps source order | the old order was a bug |
| `TriplesBlock(triples=..., triples_block=...)` | `TriplesBlock([...])` | flat list, not a linked list |
| `collect_triples()` | `collect(TriplesSameSubjectPath)` | generalised, linear, and actually works |
| `LANGTAG` | `LANG_DIR` | renamed in SPARQL 1.2, with an optional base direction |
| `SubSelectString` | `parse()` | a real parser instead of an rdflib round-trip |
| `?a=1` | `?a = 1` | operators render spaced, matching the spec's examples |
| a bare string as a term | `iri()` / `literal()` / `var()` | nothing is guessed; see the README |
| `"UNDEF"` in a `VALUES` row | the `UNDEF` node | a keyword, not a value, so `DataBlockValue` can stay precise |

The trailing `.` after the last triple of a block is no longer emitted; it is optional in
the grammar.
