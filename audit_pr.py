"""Detect breaking Python API changes between two source snapshots."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import click
import requests
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

console = Console()


class Finding(BaseModel):
    kind: str
    severity: str
    symbol: str
    file: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuditReport(BaseModel):
    old_snapshot: str
    new_snapshot: str
    findings: list[Finding] = Field(default_factory=list)

    @property
    def breaking_count(self) -> int:
        return sum(finding.severity == "breaking" for finding in self.findings)


class DefinitionCollector(ast.NodeVisitor):
    def __init__(self, relative_file: str) -> None:
        self.relative_file = relative_file
        self.module: list[str] = []
        self.definitions: dict[str, dict[str, Any]] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.module.append(node.name)
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._record_function(child)
            elif isinstance(child, ast.ClassDef):
                self.visit(child)
        self.module.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        symbol = ".".join([*self.module, node.name])
        arguments = [
            {
                "name": argument.arg,
                "kind": "positional-only"
                if argument in node.args.posonlyargs
                else "keyword-only"
                if argument in node.args.kwonlyargs
                else "positional-or-keyword",
                "annotation": ast.unparse(argument.annotation)
                if argument.annotation
                else None,
            }
            for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        ]
        self.definitions[symbol] = {
            "file": self.relative_file,
            "line": node.lineno,
            "arguments": arguments,
            "return_annotation": ast.unparse(node.returns) if node.returns else None,
        }


def collect_snapshot(snapshot: Path) -> dict[str, dict[str, Any]]:
    paths = [snapshot] if snapshot.is_file() else sorted(snapshot.rglob("*.py"))
    definitions: dict[str, dict[str, Any]] = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise click.ClickException(f"Unable to parse {path}: {error}") from error
        relative = str(path.relative_to(snapshot)) if snapshot.is_dir() else path.name
        collector = DefinitionCollector(relative)
        collector.visit(tree)
        for symbol, definition in collector.definitions.items():
            definitions[f"{relative}:{symbol}"] = definition
    return definitions


def compare_snapshots(old: Path, new: Path) -> AuditReport:
    old_definitions = collect_snapshot(old)
    new_definitions = collect_snapshot(new)
    findings: list[Finding] = []
    for key, old_definition in old_definitions.items():
        if key not in new_definitions:
            findings.append(
                Finding(
                    kind="removed_symbol",
                    severity="breaking",
                    symbol=key.split(":", 1)[1],
                    file=old_definition["file"],
                    message="Public function or method was removed.",
                )
            )
            continue
        new_definition = new_definitions[key]
        old_arguments = old_definition["arguments"]
        new_arguments = new_definition["arguments"]
        if old_arguments != new_arguments:
            findings.append(
                Finding(
                    kind="changed_parameters",
                    severity="breaking",
                    symbol=key.split(":", 1)[1],
                    file=new_definition["file"],
                    message="Function parameters or type hints changed.",
                    details={"before": old_arguments, "after": new_arguments},
                )
            )
        if old_definition["return_annotation"] != new_definition["return_annotation"]:
            findings.append(
                Finding(
                    kind="changed_return_type",
                    severity="review",
                    symbol=key.split(":", 1)[1],
                    file=new_definition["file"],
                    message="Return type hint changed and needs review.",
                    details={
                        "before": old_definition["return_annotation"],
                        "after": new_definition["return_annotation"],
                    },
                )
            )
    return AuditReport(old_snapshot=str(old), new_snapshot=str(new), findings=findings)


def ask_ollama(report: AuditReport, model: str, endpoint: str) -> str:
    prompt = (
        "Summarize this static API compatibility report in three concise maintainer actions. "
        "Do not invent findings.\n" + report.model_dump_json()
    )
    try:
        response = requests.post(
            endpoint,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("response", "")).strip() or "Ollama returned no summary."
    except requests.RequestException as error:
        raise click.ClickException(f"Ollama request failed: {error}") from error


def render_report(report: AuditReport) -> None:
    table = Table(title="RepoGuardian API audit")
    table.add_column("Severity")
    table.add_column("Symbol")
    table.add_column("Message")
    for finding in report.findings:
        table.add_row(finding.severity, finding.symbol, finding.message)
    if report.findings:
        console.print(table)
    else:
        console.print("[green]No API compatibility changes detected.[/green]")
    console.print(f"Breaking findings: {report.breaking_count}")


@click.command()
@click.argument("old_snapshot", type=click.Path(exists=True, path_type=Path))
@click.argument("new_snapshot", type=click.Path(exists=True, path_type=Path))
@click.option("--json-out", type=click.Path(path_type=Path), help="Write the JSON report to this file.")
@click.option("--ollama", is_flag=True, help="Ask a local Ollama model for a short summary.")
@click.option("--model", default="qwen2.5-coder", show_default=True)
@click.option("--endpoint", default="http://localhost:11434/api/generate", show_default=True)
def main(old_snapshot: Path, new_snapshot: Path, json_out: Path | None, ollama: bool, model: str, endpoint: str) -> None:
    """Compare OLD_SNAPSHOT and NEW_SNAPSHOT, each a .py file or source directory."""
    report = compare_snapshots(old_snapshot, new_snapshot)
    render_report(report)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        console.print(f"JSON report written to {json_out}")
    if ollama:
        console.print("[bold]Local model summary:[/bold]")
        console.print(ask_ollama(report, model, endpoint))
    if report.breaking_count:
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
