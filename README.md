# RepoGuardian Studio

[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026-f97316?style=flat-square)](https://hacktoberfest.com/)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Open%20Standard-79f2c0?style=flat-square)](https://agentskills.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-9fe870?style=flat-square)](LICENSE)

RepoGuardian Studio is a standalone browser workspace for open-source maintainers. It turns a pull-request and security auditor into a calm, human-readable interface for Hacktoberfest 2026. No build step or server is required: open `index.html` directly in a browser.

## Features

- PR Visual Diff & Code Scanner with demo fixtures for breaking API changes and secret-like patterns.
- Dependency License Checker with instant permitted, review, and restricted results.
- Local Ollama integration for `qwen2.5-coder` and `llama3.2`, plus an offline demo mode.
- Agent Skill Inspector that exposes the standard metadata and progressive-disclosure layout.
- Reference Python CLIs in `scripts/` for CI and automation.

## Quick start

1. Download or clone this repository.
2. Open `index.html` directly in Chrome, Edge, Firefox, or Safari.
3. Use **Load demo** in the scanner to see a complete review immediately.
4. Toggle **Demo mode** in the AI panel for an offline summary.

## Architecture

- `index.html`: self-contained Tailwind CDN UI, semantic HTML, and vanilla JavaScript state/actions.
- `SKILL.md`: Agent Skill Open Standard metadata, workflow, guardrails, and progressive disclosure map.
- `scripts/`: Python AST and license analyzers for maintainers who want CI integration.
- `references/`: policy sources for permitted/restricted licenses and secret scanning rules.
- `requirements.txt`: dependencies for the reference Python automation.

## Ollama setup

Install Ollama, pull a supported model, and keep the local service running:

```bash
ollama run qwen2.5-coder
```

In Studio, turn off **Demo mode**, select the model, and click **Generate summary**. The browser sends the prompt only to `http://localhost:11434/api/generate`. If the request fails, the interface keeps the report visible and explains how to return to demo mode.

## Reference CLI

```bash
python -m pip install -r requirements.txt
python scripts/audit_pr.py old-code new-code --json-out audit-report.json
python scripts/check_licenses.py requirements.txt
```

Both commands return exit code `1` when they find a breaking or restricted result. Reports never include suspected secret values. See [references/security_rules.md](references/security_rules.md).

## Contributing

1. Fork the repository and create a focused branch.
2. Add or update tests for behavior changes.
3. Run both CLIs against representative fixtures.
4. Keep reports deterministic and avoid network dependencies in tests.
5. Open a pull request describing the maintainer problem your change solves.

## Hacktoberfest 2026

RepoGuardian welcomes focused contributions that improve maintainer safety and contributor experience. Good first contributions include fixture-driven tests, accessible UI improvements, support for additional dependency inventory formats, clearer policy diagnostics, and CI integrations. Please include tests and documentation with behavior changes.

## License

RepoGuardian is released under the MIT License. See [LICENSE](LICENSE).
