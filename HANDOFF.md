# HANDOFF -- First session in the new `doc-ingest-pipeline` repository

This document is the **first thing a new agent session should read** after the folder has been moved out of the parent accelerator workspace and turned into its own GitHub repository. Work through the checklist top-to-bottom. Stop and ask the user only at the **Decision Points** explicitly marked below.

---

## 0. Context in one paragraph

`doc-ingest-pipeline` is a **headless Azure document ingestion service** carved out of [Azure-Samples/chat-with-your-data-solution-accelerator](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator) at upstream commit **`5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3`**. The carve-out scope, exclusions, and reuse map are non-negotiable -- see [`.docs/product/decisions.md`](.docs/product/decisions.md) (highest override priority) and [`component-reuse-map.md`](component-reuse-map.md).

**Spec 0001 (scaffold + port batch function entry points) is implemented but not yet verified end-to-end.** The function app imports cleanly and the test stubs assert the public contract, but `poetry.lock` is not committed and `func host start` / `azd init` have never been run.

---

## 1. Bootstrap the local environment

```pwsh
# From the repo root
poetry install                       # generates poetry.lock on first run
poetry run pre-commit install        # wire pre-commit hooks
```

Commit the freshly generated `poetry.lock` (per spec 0001 T0001-01 acceptance).

```pwsh
git add poetry.lock
git commit -m "chore: pin dependency lock file"
```

## 2. Verify the spec-0001 work

```pwsh
poetry run black --check src tests
poetry run flake8 src tests
poetry run pytest -q
```

Expected: 6 smoke tests pass (see [tests/test_function_app_smoke.py](tests/test_function_app_smoke.py)). If any fail, fix before continuing.

```pwsh
cd src/functions
func host start
```

Expected: Functions runtime starts and lists the queue trigger (`batch_push_results` on `doc-processing`) and three HTTP routes (`AddURLEmbeddings`, `BatchStartProcessing`, `combine_pages_and_chunknos`). No `ImportError`. Stop with `Ctrl+C`.

```pwsh
# Back at repo root
azd init                             # only if not already initialized
```

Expected: `azd` recognizes [`azure.yaml`](azure.yaml) and lists the `function` service.

## 3. Close out spec 0001

In [`.docs/specs/2026-06-02-scaffold-and-port-batch/tasks.md`](.docs/specs/2026-06-02-scaffold-and-port-batch/tasks.md):

- Mark T0001-09 and T0001-10 as `[x]`.
- Paste the output of `func host start` and `azd init` from step 2 into the PR description.

In [`.docs/specs/2026-06-02-scaffold-and-port-batch/spec.md`](.docs/specs/2026-06-02-scaffold-and-port-batch/spec.md):

- Flip `Status:` from `In Review` to `Complete` after the PR merges.

Open the PR:

```pwsh
git checkout -b feat/0001-scaffold-and-port-batch
git push -u origin feat/0001-scaffold-and-port-batch
gh pr create --title "feat: scaffold repo and port batch function entry points" --body-file .docs/specs/2026-06-02-scaffold-and-port-batch/spec.md
```

## 4. Decision Point -- pick the next spec

**Stop here and ask the user which path to take.** Options:

| Option | What | When to choose |
|---|---|---|
| **A. Spec 0002 (recommended)** | Port the `src/utilities/` subtree from the parent (helpers, document_loading, document_chunking, embedders, search, integrated_vectorization) minus PostgreSQL paths. Replaces all `NotImplementedError` placeholders with real delegation. | Default forward path; required before the service can actually ingest documents. Stub already exists at [`.docs/specs/NEXT-spec-0002-port-utilities/spec.md`](.docs/specs/NEXT-spec-0002-port-utilities/spec.md). |
| **B. Spec 0003 (Bicep)** | Author `infra/main.bicep` + modules so `azd up` works. | Choose only if the user wants to deploy a stub service before utilities are ported (useful for plumbing validation). |
| **C. Iterate on docs first** | Tighten roadmap, add architecture diagrams, expand best-practices. | Choose only if the user explicitly asks. |

When the user picks A, follow [`.github/instructions/create-spec.instructions.md`](.github/instructions/create-spec.instructions.md) to flesh out spec 0002 from the stub. When the user picks B, run the create-spec workflow against the roadmap's Phase 1 IaC item.

---

## Quick-reference: where things live

| What | Where |
|---|---|
| Why this repo exists | [`.docs/product/mission.md`](.docs/product/mission.md) |
| What's allowed and excluded (ADRs) | [`.docs/product/decisions.md`](.docs/product/decisions.md) |
| Roadmap | [`.docs/product/roadmap.md`](.docs/product/roadmap.md) |
| Per-file porting plan & SHA log | [`component-reuse-map.md`](component-reuse-map.md) |
| Coding rules | [`.docs/standards/code-style.md`](.docs/standards/code-style.md), [`.docs/standards/best-practices.md`](.docs/standards/best-practices.md) |
| Active spec | [`.docs/specs/2026-06-02-scaffold-and-port-batch/`](.docs/specs/2026-06-02-scaffold-and-port-batch/) |
| Next spec stub | [`.docs/specs/NEXT-spec-0002-port-utilities/spec.md`](.docs/specs/NEXT-spec-0002-port-utilities/spec.md) |
| Agent workflow rules | [`.github/instructions/`](.github/instructions/) |
| Common dev tasks | [`Makefile`](Makefile) (`make install`, `make test`, `make lint`, `make host-start`, `make precommit`) |

## Non-negotiables (read before any change)

1. **Headless contract.** No UI may be added. Any feature that requires a UI must be re-designed as an HTTP endpoint or Portal flow. (DEC-001, DEC-004)
2. **Azure AI Search only.** No `pgvector`, no Cosmos. (DEC-002)
3. **Managed identity first.** Service-to-service auth uses MI; keys only as escape hatch via EnvHelper. (DEC-005)
4. **Configuration through EnvHelper only.** Never read `os.environ` from business logic.
5. **Copy-with-attribution.** When porting a parent file, record the upstream SHA in [`component-reuse-map.md`](component-reuse-map.md) Notes column. (DEC-006)
