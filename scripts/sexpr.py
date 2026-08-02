"""S-expression output — indentation comes from nesting, never hand-typed tabs.

Two views of the same content:

- `SexprDoc` — imperative writer; one tab per nesting level. Used by the PCB,
  schematic, footprint and bitmap generators (everything in kicad10.py,
  kicad_bitmap.py and generate_kicad_project.py).
- `Sexpr` + `render_sexpr` — declarative node tree with per-format multiline
  sets, used by the shared symbol definitions (multi-line .kicad_sym file vs
  compact schematic embed).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True, slots=True)
class Sexpr:
    """One S-expression node; leaf args live in `head`, sub-nodes in `children`.

    A `str` child renders as one pre-formatted line (e.g. several compact
    nodes sharing a line), matching KiCad's mixed one-line output.
    """

    head: str
    children: tuple["Sexpr | str", ...] = ()


class SexprDoc:
    """Tab-indented writer: each nesting level adds one tab.

    Lines are stored relative to depth 0 so a doc can be re-embedded at any
    depth via `embed()`. `raw()` appends pre-formatted absolute text (e.g.
    pcbnew render_cache blocks) without re-indentation.
    """

    def __init__(self, start_depth: int = 0) -> None:
        self._lines: list[str] = []
        self._depth = start_depth

    def line(self, text: str = "") -> None:
        self._lines.append("\t" * self._depth + text)

    def blank(self) -> None:
        self._lines.append("")

    def embed(self, doc: "SexprDoc") -> None:
        pad = "\t" * self._depth
        self._lines.extend(pad + line for line in doc._lines)

    def raw(self, text: str) -> None:
        """Append pre-formatted text as-is (absolute depth, blank lines kept)."""
        self._lines.extend(text.splitlines())

    @contextmanager
    def node(self, head: str) -> Iterator[None]:
        """Emit `head` at the current depth, indent its children, close with `)`."""
        self.line(head)
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
            self.line(")")

    def render(self) -> str:
        return "\n".join(self._lines)


def render_sexpr(
    node: Sexpr,
    *,
    multiline: frozenset[str],
    depth: int = 0,
    lib_prefix: str = "",
) -> str:
    """Render a node tree; `multiline` heads with children get indented lines.

    The root, every `(symbol ...` wrapper, and depth-1 symbol heads (which also
    get `lib_prefix`, the schematic's embedded lib_id) always render multi-line.
    """
    key = node.head.split(" ", 1)[0]
    head = node.head
    if depth == 1 and key == "symbol" and lib_prefix:
        head = head.replace('symbol "', f'symbol "{lib_prefix}', 1)
    is_multiline = depth == 0 or key == "symbol" or key in multiline
    if not node.children or not is_multiline:
        return "\t" * depth + _compact(node)
    lines = ["\t" * depth + f"({head}"]
    for child in node.children:
        if isinstance(child, str):
            lines.append("\t" * (depth + 1) + child)
        else:
            lines.append(render_sexpr(child, multiline=multiline, depth=depth + 1, lib_prefix=lib_prefix))
    lines.append("\t" * depth + ")")
    return "\n".join(lines)


def _compact(node: Sexpr) -> str:
    if not node.children:
        return f"({node.head})"
    parts = [_compact(child) if isinstance(child, Sexpr) else str(child) for child in node.children]
    return f"({node.head} " + " ".join(parts) + ")"
