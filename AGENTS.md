# AI Services: agent guide

This repository is a monorepo with independently maintained service branches. Start by identifying the service, its branch, and the scope of the request. A branch contains a snapshot of the whole repository; its name does not isolate changes to one folder.

This file provides shared working instructions. Read the service README and any nested `AGENTS.md` before editing. More specific agent instructions apply within their directory; explicit user instructions take precedence. The format is described at [agents.md](https://agents.md/).

## Before making changes

1. Inspect `git status --short --branch`. Preserve existing user changes and identify the current base before switching branches.
2. Identify the target service and the intended development branch. Inspect available local and remote references; refresh remote references when needed before preparing an integration.
3. Read the closest `AGENTS.md`, the service README, and the relevant implementation/configuration. Documentation can lag behind code.
4. Define the smallest affected scope. Do not modify another service, shared automation, or deployment configuration unless the task requires it.
5. Identify the service's actual dependency manager, entry point, checks, and external dependencies. There is no single repository-wide install, build, or test command established here.

For analysis or read-only requests, inspect and explain without editing files or changing branches.

## Branch and integration workflow

The normal service integration path is:

```text
task branch based on the service's dev branch
    → dev-<service> → main-<service> → staging → main
```

Actual branch names are not always identical to directory names. Known pairs include:

| Service directory | Development branch | Service main branch |
| --- | --- | --- |
| `ai-feedback-service/` | `dev-feedback` | `main-feedback` |
| `ai-insights-service/` | `dev-ai-insights` | `main-ai-insights` |
| `ar-generator-service/` | `dev-ar-generator` | `main-ar-generator` |
| `fast-response-service/` | `dev-fast-response` | `main-fast-response` |
| `mapping-service/` | `dev-mapping` | `main-mapping` |
| `partner-request-support/` | `dev-partner-request-support` | `main-partner-request-support` |
| `qa-service/` | `dev-qa` | `main-qa` |
| `text-mining-service/` | `dev-text-mining` | `main-text-mining` |

Verify these names against current references. For `chatbot-service/`, both `dev-chatbot` and `dev-chatbot-service` references exist; confirm the intended development line for `main-chatbot-service`. `admin-module/` has a `dev-admin-module` reference, but a matching service-main branch is not established here. Confirm the workflow for `clarisa-agresso-service/` rather than inferring one from its name.

- Prepare service work from its development branch, using a focused task branch when appropriate. Follow a different base when explicitly requested.
- Development-to-service-main merges are handled by the maintainer unless explicitly delegated. Preparing documentation does not authorize release merges or deployments.
- Before any authorized merge, inspect all incoming commits and the complete diff. A documentation merge can also carry unreleased code or intentional environment differences.
- After the maintainer's local development-to-service-main merge and before push, compare the resulting service-main with development. Check missing tests/interfaces, route changes, dependencies, and environment destinations; adapt the service-main README and agent guides to its actual tree while preserving deliberate differences.
- Do not merge all of `main` into a service development branch merely to obtain documentation. Bring only the intended documentation changes when authorized.
- Never reset, discard, or rewrite user work as part of switching branches or resolving conflicts.

`main` is the consolidated reference after integration. Its updated files are not automatically available on every service branch. Some service branches may lack newer service directories or nested agent guides.

## Documentation ownership

- Root `README.md`: monorepo overview, service index, and shared navigation.
- Root `AGENTS.md`: shared working rules and branch workflow.
- `<service>/README.md` and `<service>/docs/`: version-specific setup, contracts, architecture, and operations.
- `<service>/AGENTS.md`: implementation map, checks, and service-specific constraints for agents.

Maintain service documentation alongside its code and promote them together through the service's integration path. Prepare shared documentation independently for integration through `staging` to `main`; keep shared and service-specific changes separable in commits and review.

Add service-specific agent guides as each service is reviewed. Preserve existing nested guides, including those under Text Mining when present; do not replace them with assumptions copied from another service.

Link to maintained documentation instead of duplicating large API schemas, dependency lists, or environment instructions. Verify claims against the current branch. Distinguish implemented behavior, historical design, proposed changes, and live deployment checks.

## Implementation and dependency conventions

- Match the existing service's structure, naming, formatting, and error-handling patterns. Avoid unrelated refactors.
- Install and run dependencies from the relevant service or frontend directory. Inspect its manifests and lockfiles first.
- Python services may contain `pyproject.toml`, `uv.lock`, and `requirements.txt`. Check which files the Dockerfile actually installs; keep affected dependency declarations consistent when changing dependencies.
- Frontends have their own package manifests and lockfiles. Use their defined scripts and package manager rather than assuming one tool across the monorepo.
- Identify the real local HTTP entry point. A Lambda `main.handler` or Dockerfile is not necessarily a local Uvicorn command.
- Keep public contracts compatible unless the request includes changing them. Review affected callers, schemas, prompts, examples, and documentation together when a contract changes.
- Treat prompts, model IDs, criteria, scoring, and authentication changes as behavior changes, even when they involve only strings or configuration.

## Validation and external effects

Read relevant test scripts before running them. Distinguish local checks, stubbed integration checks, and calls to live systems. Some scripts contact deployed services, invoke paid models, or write data.

Run checks appropriate to the changed scope. For documentation, verify local links, commands, examples, and consistency with code. For behavior changes, run relevant existing tests and add targeted coverage when needed. Do not claim a deployment works based only on a local or stubbed test.

GitHub Actions under `.github/workflows/` can invoke Jenkins on pushes or pull requests. Inspect the actual branch and event filters for the affected service; documentation-only changes can trigger Jenkins. Do not assume workflow display names, filenames, and target jobs always agree.

Report what changed, which checks ran, their results, and material validation limits. State the current branch and whether changes were committed, pushed, or merged. Keep those operations within the user's requested scope.

## Configuration and data handling

- Keep `.env` files, credentials, API keys, and webhook secrets out of commits and examples. Use fictional payloads and placeholders.
- Preserve authentication and input-validation behavior unless the requested change includes it. Frontend authentication does not establish that a backend route enforces access control.
- Avoid committing downloaded evidence, logs, temporary databases, generated build output, or real reporting data.
- Inspect how configuration is consumed: an environment-variable name in a README does not prove it overrides a hardcoded client setting.
- Avoid displaying secrets or full sensitive payloads in logs and command output. Report configuration requirements by name rather than revealing values.
