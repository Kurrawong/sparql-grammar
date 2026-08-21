# Browser demo

A [JupyterLite](https://jupyterlite.readthedocs.io/) site: the notebooks in `notebooks/`
run in the browser on Pyodide, with no server and nothing to install. That works because
the library is pure Python with no runtime dependencies — and because `lark`, needed for
the `parse` extra, is pure Python too.

Published by `.github/workflows/deploy-demo.yml` on every push to the default branch.

## Editing the notebooks

The demos are written as plain Python in `src/`, not as notebook JSON, so the code can be
run and tested like any other code. Cells are delimited by `# %%`, and `# %% [markdown]`
starts a prose cell. `test_demos.py` runs in CI before the site is built, so a demo that
raises cannot be published.

```shell
python demo/build_notebooks.py     # src/*.py -> notebooks/*.ipynb
python demo/test_demos.py          # run every cell, offline
```

## Building the site locally

The package is not on PyPI yet, so the site carries its own wheels: both must be passed
to `--piplite-wheels` or `piplite.install` will fail in the browser.

```shell
pip install -r demo/requirements-build.txt
python -m build --wheel --outdir demo/files .                     # the wheel Pyodide installs
pip download lark --no-deps --only-binary=:all: --dest demo/files  # for the parse extra
cd demo && jupyter lite build --contents notebooks \
    $(for w in files/*.whl; do echo --piplite-wheels $w; done) --output-dir ../_site
python -m http.server --directory ../_site
```
