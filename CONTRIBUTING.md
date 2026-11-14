# Contributing (branching and commit rules in brief)

Full strategy: [docs/project-management/GIT_STRATEGY.md](docs/project-management/GIT_STRATEGY.md).

## Branches

| Branch | Purpose |
|---|---|
| `main` | Reviewed, tagged, submittable work; changed only by pull request |
| `develop` | Integration of completed work |
| `feature/<topic>` | New functionality, from `develop`, merged back by pull request (lifetime up to 5 days) |
| `docs/<topic>` | Documentation and evidence (up to 3 days) |
| `fix/<topic>` | Defects found on `develop` (up to 2 days) |
| `hotfix/<topic>` | Defects in a tagged release, from `main`, merged to `main` and `develop` |

## Commit messages (Conventional Commits)

```text
<type>(<scope>): <imperative summary, up to 72 characters>

<body: what and why>

Refs: FR-23, NFR-03
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `ci`, `chore`, `style`, `revert`.
Scopes: module names (`analyzer`, `testgen`, `scriptgen`, `executor`, `healing`, `failure`, `reporting`, `dashboard`), services (`gateway`, `masking`, `persistence`, `audit`, `orchestrator`, `cli`), or `core`, `ci`, `docs`, `evidence`, `deps`.

## Pull requests

Use the template. Reference the requirement IDs, update documentation, register evidence, and confirm there are no secrets, client names or client data.

## Tags

Annotated tags on `main` only: release tags `v0.1.0`, `v0.5.0`, `v1.0.0-rc1`, `v1.0.0` and submission snapshots `unitN-submitted`.
