"""``book`` package marker.

Quarto chunks under ``book/chapters/*.qmd`` import the artifact loaders and
plot helpers as ``from book._helpers import ...``. Marking this directory as
a regular package (instead of an implicit namespace package) keeps the
import path deterministic when the chunks run from ``book/_book/`` cache
locations and avoids surprises with editable installs.

There is no public top-level API here; consumers should reach into the
``book._helpers`` submodule directly.
"""
