"""Check dependency declarations against a JSON license policy."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import click
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

console = Console()


class LicenseFinding(BaseModel):
    package: str
    declared_license: str
    status: str
    message: str


class LicenseReport(BaseModel):
    source: str
    findings: list[LicenseFinding] = Field(default_factory=list)

    @property
    def restricted_count(self) -> int:
        return sum(finding.status == "restricted" for finding in self.findings)


def load_policy(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise click.ClickException(f"Unable to read policy {path}: {error}") from error


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(('#', '-r', '--')):
            continue
        name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip()
        if name:
            entries.append((name, "UNKNOWN"))
    return entries


def load_dependencies(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise click.ClickException(f"Unable to read dependency report {path}: {error}") from error
        dependencies = payload.get("dependencies", payload) if isinstance(payload, dict) else payload
        if not isinstance(dependencies, list):
            raise click.ClickException("JSON dependency input must be a list or an object with dependencies.")
        result: list[tuple[str, str]] = []
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not dependency.get("name"):
                raise click.ClickException("Each JSON dependency must contain a name.")
            result.append((str(dependency["name"]), str(dependency.get("license", "UNKNOWN"))))
        return result
    return parse_requirements(path)


def check_dependencies(source: Path, policy_path: Path) -> LicenseReport:
    policy = load_policy(policy_path)
    permitted = set(policy.get("permitted", []))
    restricted = set(policy.get("restricted", []))
    findings: list[LicenseFinding] = []
    for package, license_name in load_dependencies(source):
        if license_name in restricted:
            status = "restricted"
            message = "Requires maintainer and legal review."
        elif license_name in permitted:
            status = "permitted"
            message = "Allowed by the configured policy."
        else:
            status = "unknown"
            message = "License is not present in the configured policy."
        findings.append(LicenseFinding(package=package, declared_license=license_name, status=status, message=message))
    return LicenseReport(source=str(source), findings=findings)


def render_report(report: LicenseReport) -> None:
    table = Table(title="RepoGuardian license audit")
    table.add_column("Package")
    table.add_column("License")
    table.add_column("Status")
    for finding in report.findings:
        table.add_row(finding.package, finding.declared_license, finding.status)
    console.print(table)
    console.print(f"Restricted findings: {report.restricted_count}")


@click.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("--policy", "policy_path", default="references/license_policy.json", type=click.Path(exists=True, path_type=Path), show_default=True)
@click.option("--json-out", type=click.Path(path_type=Path), help="Write the JSON report to this file.")
def main(source: Path, policy_path: Path, json_out: Path | None) -> None:
    """Check a requirements.txt or dependency inventory JSON file."""
    report = check_dependencies(source, policy_path)
    render_report(report)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        console.print(f"JSON report written to {json_out}")
    if report.restricted_count:
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
