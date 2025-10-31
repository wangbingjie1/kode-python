"""Jupyter Notebook tools."""

import json
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class NotebookReadInput(BaseModel):
    """Input for NotebookReadTool."""

    notebook_path: str = Field(description="Path to Jupyter notebook (.ipynb)")
    include_outputs: bool = Field(
        default=True, description="Include cell outputs (default: True)"
    )


class NotebookReadTool(KodeTool):
    """
    Read Jupyter notebooks.

    Equivalent to TypeScript's NotebookReadTool
    """

    name: str = "NotebookRead"
    description: str = """Read Jupyter notebook (.ipynb) files.
- Reads code cells and markdown cells
- Can include or exclude outputs
- Shows cell execution order
- Returns formatted notebook content"""
    args_schema: Type[BaseModel] = NotebookReadInput
    requires_permission: bool = False

    def _run(self, notebook_path: str, include_outputs: bool = True) -> str:
        """Read notebook content."""
        try:
            path = Path(notebook_path)
            if not path.exists():
                return f"Error: Notebook not found: {notebook_path}"

            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            cells = notebook.get("cells", [])
            if not cells:
                return f"Notebook is empty: {notebook_path}"

            result = [f"Notebook: {notebook_path}", f"Cells: {len(cells)}", "=" * 60, ""]

            for i, cell in enumerate(cells, 1):
                cell_type = cell.get("cell_type", "unknown")
                source = cell.get("source", [])

                # Convert source to string
                if isinstance(source, list):
                    source_text = "".join(source)
                else:
                    source_text = str(source)

                # Add cell header
                execution_count = cell.get("execution_count")
                if execution_count:
                    result.append(f"Cell {i} [{cell_type}] (executed: {execution_count}):")
                else:
                    result.append(f"Cell {i} [{cell_type}]:")

                result.append(source_text)

                # Add outputs if requested
                if include_outputs and cell_type == "code":
                    outputs = cell.get("outputs", [])
                    if outputs:
                        result.append("\nOutput:")
                        for output in outputs:
                            output_type = output.get("output_type", "")
                            if output_type == "stream":
                                text = "".join(output.get("text", []))
                                result.append(text)
                            elif output_type == "execute_result" or output_type == "display_data":
                                data = output.get("data", {})
                                text = data.get("text/plain", [""])[0]
                                result.append(text)
                            elif output_type == "error":
                                ename = output.get("ename", "")
                                evalue = output.get("evalue", "")
                                result.append(f"Error: {ename}: {evalue}")

                result.append("\n" + "-" * 60 + "\n")

            return "\n".join(result)

        except Exception as e:
            return f"Error reading notebook: {str(e)}"


class NotebookEditInput(BaseModel):
    """Input for NotebookEditTool."""

    notebook_path: str = Field(description="Path to Jupyter notebook")
    cell_index: int = Field(description="Cell index to edit (0-based)")
    new_source: str = Field(description="New cell source code/markdown")
    cell_type: Optional[str] = Field(
        default=None, description="Cell type (code or markdown), optional"
    )


class NotebookEditTool(KodeTool):
    """
    Edit Jupyter notebook cells.

    Equivalent to TypeScript's NotebookEditTool
    """

    name: str = "NotebookEdit"
    description: str = """Edit cells in Jupyter notebooks.
- Replace cell content by index
- Can change cell type (code/markdown)
- Preserves notebook structure
- Cell index is 0-based"""
    args_schema: Type[BaseModel] = NotebookEditInput
    requires_permission: bool = True

    def _run(
        self,
        notebook_path: str,
        cell_index: int,
        new_source: str,
        cell_type: Optional[str] = None,
    ) -> str:
        """Edit notebook cell."""
        try:
            path = Path(notebook_path)
            if not path.exists():
                return f"Error: Notebook not found: {notebook_path}"

            # Read notebook
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            cells = notebook.get("cells", [])
            if cell_index < 0 or cell_index >= len(cells):
                return f"Error: Cell index {cell_index} out of range (0-{len(cells)-1})"

            # Update cell
            cell = cells[cell_index]

            # Update source
            if isinstance(new_source, str):
                cell["source"] = new_source.split("\n")
            else:
                cell["source"] = new_source

            # Update cell type if provided
            if cell_type:
                if cell_type not in ["code", "markdown"]:
                    return f"Error: Invalid cell type: {cell_type}. Must be 'code' or 'markdown'"
                cell["cell_type"] = cell_type

                # Clear outputs if changing to markdown
                if cell_type == "markdown":
                    cell.pop("outputs", None)
                    cell.pop("execution_count", None)

            # Write notebook
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1)

            return f"Successfully updated cell {cell_index} in {notebook_path}"

        except Exception as e:
            return f"Error editing notebook: {str(e)}"
