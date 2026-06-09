"""Execute CRPTO notebooks without mutating canonical artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOKS = ("10_crpto_cp_robust_opt.ipynb",)


def execute_notebook(input_path: Path, output_path: Path, *, timeout_s: int) -> None:
    notebook = nbformat.read(input_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout_s,
        kernel_name="python3",
        resources={"metadata": {"path": str(input_path.parent)}},
    )
    client.execute()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute CRPTO notebooks in a sandbox.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--output-dir", default="reports/notebook_exec")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    notebooks_dir = repo_root / "notebooks"
    output_dir = repo_root / args.output_dir

    for notebook_name in NOTEBOOKS:
        input_path = notebooks_dir / notebook_name
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        output_path = output_dir / notebook_name
        execute_notebook(input_path, output_path, timeout_s=int(args.timeout))
        print(f"[crpto-notebook-suite] saved {output_path}")


if __name__ == "__main__":
    main()
