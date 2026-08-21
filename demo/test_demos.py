"""Run every demo cell offline, so a broken demo cannot be published.

Covers both browser demos: the notebook sources in ``src/``, and the editors in
``embed.html``.

The notebooks call ``piplite.install``, which only exists in the browser; here the
package is already importable, so the call is stubbed out. Top-level ``await`` is
wrapped in a coroutine to make it executable.

Each ``embed.html`` editor is executed in a *fresh* namespace, because PyScript gives
each editor its own. An example that leans on a name it does not import works only by
accident of run order, and that cannot be seen without loading the page.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import io
import re
import sys
import textwrap
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from build_notebooks import split_cells  # noqa: E402


def _stub_piplite() -> None:
    module = types.ModuleType("piplite")

    async def install(*args, **kwargs):
        return None

    module.install = install
    sys.modules["piplite"] = module


def _executable(body: str) -> str:
    """Wrap top-level await so exec() accepts it."""
    if not re.search(r"^\s*await ", body, re.M):
        return body
    indented = "\n".join(f"    {line}" for line in body.splitlines())
    return (
        "import asyncio as _asyncio\n"
        f"async def _cell():\n{indented}\n"
        "_asyncio.get_event_loop().run_until_complete(_cell())"
    )


def _embed_editors(page: Path) -> list[tuple[str, str]]:
    """The (label, code) of every py-editor in the page, setup editors excluded."""
    editors = re.findall(
        r'<script type="py-editor"([^>]*)>(.*?)</script>', page.read_text(), re.S
    )
    runnable = [
        body
        for attributes, body in editors
        if "setup" not in attributes  # needs pyscript and a live interpreter
    ]
    return [
        (f"example {number}", textwrap.dedent(html.unescape(body)).strip())
        for number, body in enumerate(runnable, 1)
    ]


def main() -> int:
    _stub_piplite()
    asyncio.set_event_loop(asyncio.new_event_loop())
    failures = 0
    for source in sorted((HERE / "src").glob("*.py")):
        namespace: dict = {"__name__": "__demo__"}
        cells = [body for kind, body in split_cells(source.read_text()) if kind == "code"]
        print(f"{source.name}: {len(cells)} code cells")
        for number, body in enumerate(cells, 1):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(  # noqa: S102
                        compile(_executable(body), f"{source.name}:cell{number}", "exec"),
                        namespace,
                    )
            except Exception as error:  # noqa: BLE001
                failures += 1
                print(f"  cell {number} FAILED: {type(error).__name__}: {error}")
    page = HERE / "embed.html"
    editors = _embed_editors(page)
    print(f"{page.name}: {len(editors)} editors")
    for label, code in editors:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(  # noqa: S102
                    compile(code, f"{page.name}:{label}", "exec"),
                    {"__name__": "__demo__"},
                )
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"  {label} FAILED: {type(error).__name__}: {error}")

    print("all demo cells ran" if not failures else f"{failures} failing cells")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
