---
name: repoguardian
description: Review open-source pull requests for breaking API changes, dependency license risks, and exposed API secrets using a local-first web workspace.
version: 1.0.0
author: RepoGuardian contributors
---

# RepoGuardian Studio

RepoGuardian is an open-source maintainer skill for Hacktoberfest 2026. Use RepoGuardian Studio when a maintainer needs a clear, repeatable review of pull-request code, dependency licenses, or likely API-secret leaks without sending source code to a hosted service.

## Core workflow

1. Paste base and proposed code into the PR Scanner and run the local static checks.
2. Review breaking API changes and secret-like patterns before merging.
3. Add package names and licenses to the Dependency License Checker.
4. Use the Ollama panel for a local summary when `qwen2.5-coder` or `llama3.2` is available.
5. Treat every finding as advisory and confirm it with tests and maintainer review.

## Progressive disclosure

- `index.html` is the standalone interface and runs directly in a browser.
- `scripts/` contains the reference Python CLI analyzers for automation.
- `references/` contains license and security policy details.
- `README.md` contains setup, architecture, and contributor guidance.

## Guardrails

- Treat static analysis and local-model summaries as advisory: confirm findings with project tests and maintainer review.
- Never print secret values in reports.
- Keep analysis local by default. Ollama is optional and must point to `http://localhost:11434`.
- Add or update focused tests when changing detection behavior or policy.
