# Browser demo

The library takes two shapes in a browser, both served from this directory and both
working because the package is pure Python with no runtime dependencies — as is `lark`,
so the `parse` extra runs there too.

| | what it is | locally | published at |
|---|---|---|---|
| `embed.html` | a plain page whose code blocks are editable and runnable — no notebook, no IDE | `just embed` | `/embed/` |
| `notebooks/` | a [JupyterLite](https://jupyterlite.readthedocs.io/) site: file browser, multiple notebooks, persistent kernel | `just serve` | `/lab/index.html` |

`.github/workflows/deploy-demo.yml` publishes both on every push to the default branch.

## embed.html

PyScript boots one Pyodide interpreter, a hidden `setup` editor installs the wheels
listed in `files/pyscript.json`, and every editor on the page shares that interpreter.
Two constraints worth knowing before editing it:

- The editors run in a **worker**, so `window` and `document` need `SharedArrayBuffer`,
  which needs cross-origin isolation. `mini-coi.js` is vendored here to supply those
  headers from any static host, GitHub Pages included. It must be same-origin, so it
  cannot come from a CDN.
- micropip in a worker cannot resolve a relative wheel URL, so the setup editor builds
  absolute ones rather than declaring packages in a PyScript `config`. It resolves them
  against the page's own directory, not `window.location.origin`, because a project Pages
  site is served under a `/<repo>/` prefix that `origin` would drop. Every other path in
  the page is relative for the same reason, so it works at a server root and under a
  prefix alike.

## The notebooks

Written as plain Python in `src/`, not notebook JSON, so the code runs and tests like any
other code. Cells are delimited by `# %%`, and `# %% [markdown]` starts a prose cell.
The `piplite.install` cell is a no-op outside Pyodide, so they also run against a normal
checkout — `just lab` layers JupyterLab over the project venv rather than adding it as a
dependency.

```shell
just build-notebooks    # src/*.py -> notebooks/*.ipynb
just test-demos         # run every cell, offline
just check-demos        # what CI enforces: notebooks in sync with src/, and every cell runs
just lab                # open them in a local JupyterLab
```

`test_demos.py` runs in CI before the site is built, so a demo that raises cannot be
published.

## Building the site

`just wheels` builds the two wheels Pyodide installs and regenerates
`files/pyscript.json`, so the wheel version is never spelled out in `embed.html`. `just
site` bundles them into `_site/` (each wheel needs its own `--piplite-wheels` flag, which
the recipe handles) and stages `embed.html` into `_site/embed/` with its own copy of the
assets — its own directory because JupyterLite already writes notebook contents to
`_site/files/`, and because mini-coi's service worker scope is the directory it is served
from. `just serve` builds and serves the lot; `just clean` drops the artefacts.

To check the published layout rather than the local one, serve the built site from inside
a directory named after the repository and open `/sparql-grammar/embed/` — that is the
only way the `/<repo>/` prefix gets exercised.
