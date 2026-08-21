# sparql-grammar

Typed Python objects for the [SPARQL 1.2](https://www.w3.org/TR/sparql12-query/) grammar:
one class per W3C production, each able to render itself back to SPARQL. Build queries as
data, change them programmatically, print them for a machine or for a person.

No runtime dependencies. No pydantic.

**[Try it in your browser](https://kurrawong.github.io/sparql-grammar/lab/index.html)** —
notebooks on Pyodide, nothing to install. (Live once Pages is enabled; see `demo/`.)

```python
from sparql_grammar import iri, optional, select, var

concept, label, parent = var("concept"), var("label"), var("parent")

query = select(
    concept, label,
    where=[
        (concept, "a", iri("skos:Concept")),
        (concept, iri("skos:prefLabel"), label),
        optional((concept, iri("skos:broader"), parent)),
    ],
    limit=10,
    prefixes={"skos": "http://www.w3.org/2004/02/skos/core#"},
)

print(query.to_pretty_string())
```

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?concept ?label
WHERE {
  ?concept a skos:Concept .
  ?concept skos:prefLabel ?label
  OPTIONAL {
    ?concept skos:broader ?parent
  }
}
LIMIT 10
```

## Installing

```shell
pip install sparql-grammar             # core, no dependencies
pip install sparql-grammar[parse]      # + SPARQL text -> objects (lark)
pip install sparql-grammar[rdflib]     # + rdflib term conversion
```

## Two ways in, two ways out

Write the objects, or write SPARQL and get the objects:

```python
from sparql_grammar import parse            # pip install sparql-grammar[parse]

query = parse("SELECT ?s WHERE { ?s a <http://ex/C> } LIMIT 10")
query.query.query.solution_modifier.limit_offset.limit_clause.limit = INTEGER("100")
print(query)                                # ... LIMIT 100
```

`to_string()` is the canonical, cheap rendering for an endpoint; `to_pretty_string()`
indents it for a human. Layout costs nothing unless asked for.

## Writing less

The grammar is verbose by nature — a `FILTER` comparison sits nine levels down the
expression tower. Builders live on the production they build, so the tower is never
spelled out by hand:

```python
Expression.compare(var("count"), "=", 101)      # ?count = 101
Expression.all_of(a, b, c)                      # a && b && c
Expression.negate(is_blank(var("node")))        # !isBLANK(?node)
PathAlternative.seq(iri("ex:a"), iri("ex:b"))   # ex:a/ex:b
PathAlternative.mod(iri("ex:broader"), "+")     # ex:broader+
Aggregate.count(var("x"), distinct=True)        # COUNT(DISTINCT ?x)
```

`sparql_grammar.helpers` adds the cross-production shorthands — `triple`, `values`,
`filter_`, `optional`, `union`, `graph`, `service`, `bind`, `select`, `construct`,
`modify`. Every one returns ordinary grammar nodes, so results stay inspectable, mutable
and hashable.

## Terms are explicit — no string is ever interpreted

`var()`, `iri()` and `literal()` say which term you mean, exactly as rdflib makes you
choose between `URIRef` and `Literal`. A bare string in a term position is a `TypeError`
naming the constructor to reach for:

```python
triple(var("s"), iri("skos:broader"), literal("x"))   # say what each one is
triple("?s", "skos:broader", "x")                     # TypeError, three times over
```

The reason is not tidiness. Reading a string by its shape lets the *value* choose its
role in the query:

| written | read as | but the caller may have meant |
|---|---|---|
| `"<http://ex/admin>"` | an IRI | the literal `"<http://ex/admin>"` |
| `"?anything"` | a variable | the literal `"?anything"` |
| `"skos:broader"` | a literal | the IRI `skos:broader` |

The variable case is the dangerous one: `VALUES ?name { "Alice" }` constrains a query,
while `VALUES ?name { ?anything }` removes the constraint altogether — so one untrusted
value beginning with `?` rewrites the query rather than parameterising it. Escaping
cannot help, because nothing is being escaped; only the caller knows the type.

What still needs no ceremony: `int`, `float` and `bool` (the Python type already says
which literal it is); `"a"` in predicate position (a keyword for `rdf:type`); a name
where the grammar allows nothing but a variable (`select("?s", …)`, `bind(expr,
"?count")`, `values("x", […])`); and surface form within one type — `iri("http://x")`
and `iri("skos:broader")` are both IRIs, `var("s")` and `var("?s")` the same variable.

`INTEGER` really is a term, surprising as the name sounds: the alternations below
`VarOrTerm` are union aliases, so it appears there directly. A bare `5` in a triple is
an `INTEGER` token per the spec.

## Untrusted input

The usual shape is a skeleton built once from values the program controls, with inputs
substituted per request, which makes the term constructors the only place input safety
matters. Three jobs to do there:

**Text can be escaped, so it always is** — a string literal is safe to build from
hostile input with no ceremony:

```python
literal('x" . ?s ?p ?o . #')     # -> "x\" . ?s ?p ?o . #"   one literal, still
```

**IRIs, variable names and language tags cannot be escaped** — there is no syntax for
it — so a bad one can only be refused. The string-accepting helpers validate by
default:

```python
iri("http://x> . ?s ?p ?o . <http://y")   # ValidationError
var("s . ?x ?y")                          # ValidationError
literal("x", lang='en" . #')              # ValidationError
```

**And the type of the term is never taken from the input**, per the section above — a
parameter cannot promote itself from a literal to an IRI, or to a variable. So:

```python
template = select(                                                    # once, trusted
    var("s"), where=[(var("s"), iri("ex:p"), var("value"))]
)
...
row = values("value", [iri(v) for v in request_values])               # per request
```

Checking costs about 0.3 µs per term. Pass `check=False`, or use the production
constructors (`IRI(...)`, `Var(...)`) which never validate, for values the program
produced itself.

## Whole-tree validation is opt-in

Beyond the per-term checks above, a tree can be validated on demand — for tests and
development; it is not cheap.

```python
node.validate("terminals")           # terminal values against their spec regex
node.validate("full")                # terminals plus every field's type

with debug_validation("terminals"):  # or check as each node is constructed
    ...
with debug_validation():             # "full" is the default level
    ...
```

On a 400-triple query (min-of-5): a plain build is 1.98 ms;
`debug_validation("terminals")` while building 2.58 ms and full 13.7 ms;
`validate("terminals")` as a pass adds 8.6 ms, `validate("full")` 20.7 ms. Full
construction-time validation costs about what the *old* library's always-on validation
cost (15.7 ms) — being opt-in is where most of the build speedup comes from, so leave it
off in production. `debug_validation("terminals")` is the one cheap enough to develop
with.

Constraints that types cannot express are checked here rather than left unenforced:
`SEPARATOR` only on `GROUP_CONCAT`, `*` only on `COUNT`, `MODIFY` needing a `DELETE` or
`INSERT` clause, a literal having a language *or* a datatype. All were broken or
unenforceable before.

## Why the rebuild

The successor to `sparql-grammar-pydantic`, rebuilt after measuring the original under
the load its main consumer actually puts on it (building query trees on every HTTP
request). The headline turned out **not** to be pydantic; dropping it accounts for
roughly a seventh of the improvement. The rest came from two structural fixes: rendering
by appending into one buffer rather than delegating through a chain of generators, and
modelling recursive productions as flat lists rather than linked lists.

| | before | now |
|---|---|---|
| Node type | pydantic `BaseModel` | `dataclass(slots=True)` |
| Per-node memory | 80 B + `__dict__` | 40 B |
| Rendering | generator `yield from` chains | append into one buffer |
| Recursive productions | linked lists, quadratic, hard ceiling | flat lists, linear |
| Validation | always on, partly broken | opt-in, two levels |
| Hashing | hand-written on ~30 classes, most unhashable | structural, every node hashable |
| Grammar coverage | 69% of SPARQL 1.1 | 100% of SPARQL 1.2, machine-checked |
| UPDATE | declared but unconstructible | complete |

`benchmarks/bench.py` renders **the same query** from both libraries using both real
class trees (a prez-shaped `CONSTRUCT` + `WHERE`), and refuses to report timings if they
diverge:

| triples | | 0.1.11 | this | |
|---|---|---|---|---|
| 400 | build | 15.7 ms | 2.0 ms | 7.7× |
| 400 | render | 39–65 ms | 0.9 ms | 45–76× |
| 400 | deepcopy | 36.4 ms | 5.6 ms | 6.5× |
| 400 | equality | 7.2 ms | 0.8 ms | 9.2× |
| 400 | collect triples | 256 ms | 5.2 ms | 49× |
| 400 | hash | unhashable | 0.5 ms | — |
| 800 | render | 148.8 ms | 1.9 ms | 79× |
| 10,000 | render | 21.6 **s** | 12.7 ms | 1700× |

Also at 400 triples: tree memory 2016 KB → 382 KB, 1.63× fewer nodes (bare alternations
are union aliases rather than wrapper classes, so a term goes straight where the grammar
allows one), formatted rendering 1.3 ms, parsing 0.67 ms under LALR. Import takes ~100
ms. The old render time swings between 39 ms and 65 ms across runs — it allocates
heavily and is sensitive to GC state — so the conservative figure is quoted.

The gap grows with query size because the old rendering was quadratic: per doubling of
input its render time grew 3.3–3.7×, this one 1.8–2.2×. It also hit `RecursionError` a
little past a thousand triples; there is no such ceiling here.

## Grammar coverage is a fact, not a claim

`spec/sparql.bnf` is the W3C machine-readable grammar, vendored verbatim, and
`tools/audit.py` checks the implemented classes against it:

```
$ python tools/audit.py
coverage: 194/194 productions implemented (100%) - 156 classes, 38 alternation aliases

$ python tools/audit.py --lark
parser grammar: 194/194 spec productions have a rule (100%)
```

The same check covers the parser grammar and reports every rule it adds beyond the spec
— that grammar began life elsewhere, so this is how it earns trust rather than being
taken on faith. It has already caught nine unreachable rules and one production that
SPARQL 1.2 removed.

Field names and shapes are hand-written on purpose: EBNF names productions but not their
parts, so generated classes end up with positional, anonymous fields — precisely what
made the previous API awkward. The grammar file proves *completeness*; people design the
*API*. (`tools/audit.py --skeleton` still writes the boring first draft.)

## Testing

```shell
pytest                       # 500+ tests
python tools/audit.py        # grammar coverage
python benchmarks/bench.py   # against 0.1.11
```

The parser is checked against the W3C syntax test suites and the spec's own examples —
941 queries. All parse, and all re-render, formatted or not, to text that parses back to
the same tree. 16 of the 27 invalid queries in the negative suite are correctly
rejected; the grammar is more permissive than the spec in the rest, asserted in the
tests so it cannot quietly get worse.

## The browser demo

`demo/` holds a [JupyterLite](https://jupyterlite.readthedocs.io/) site that runs the
library in the browser, published to GitHub Pages by `.github/workflows/deploy-demo.yml`.
It works because the package is pure Python with no runtime dependencies — as is `lark`,
so the `parse` extra runs there too. The notebooks are written as plain Python in
`demo/src/`, so CI regenerates them, checks they are not stale, and runs every cell
before publishing.

## Migrating from sparql-grammar-pydantic

Most call sites are unchanged. See [MIGRATING.md](MIGRATING.md) for the differences.

## Licence

BSD-3-Clause.
