# Custom Instructions and Tweaks go here.

> **Portable copy** - this file ships with the `doc-ingest-pipeline/` folder. When the folder is moved to its own repository, this file should land at `.github/copilot-instructions.md` at the new repo root and the relative paths below will resolve correctly.

## doc-ingest-pipeline Details

### Product Context
- **Mission & Vision:** [mission](../.docs/product/mission.md)
- **Technical Architecture:** [tech-stack](../.docs/product/tech-stack.md)
- **Development Roadmap:** [roadmap](../.docs/product/roadmap.md)
- **Decision History:** [decisions](../.docs/product/decisions.md)
- **Component Reuse Map:** [component-reuse-map](../component-reuse-map.md)

### Development Standards
- **Code Style:** [code-style](../.docs/standards/code-style.md)
- **Best Practices:** [best-practices](../.docs/standards/best-practices.md)

### Project Management
- **Active Specs:** [.docs/specs/](../.docs/specs/)
- **Spec Planning:** Follow [create-spec.instructions.md](./instructions/create-spec.instructions.md).
- **Task Execution:** Follow [execute-tasks.instructions.md](./instructions/execute-tasks.instructions.md).
- **Memory & Workflow:** Follow [memory-workflow.instructions.md](./instructions/memory-workflow.instructions.md).
- **Sequential Thinking:** Follow [sequential-thinking-workflow.instructions.md](./instructions/sequential-thinking-workflow.instructions.md) when using the `sequentialthinking` MCP tool.
- **Commit Messages:** Follow [commit-message.instructions.md](./instructions/commit-message.instructions.md) (Conventional Commits).
- **Python Code:** Follow [languages/python.instructions.md](./instructions/languages/python.instructions.md).

## Workflow Instructions

When asked to work on this codebase:

1. **First**, check the [roadmap](../.docs/product/roadmap.md) for current phase and priorities.
2. **Then**, consult the [component-reuse-map](../component-reuse-map.md) before writing new code - the answer may already exist upstream in `Azure-Samples/chat-with-your-data-solution-accelerator`.
3. **Then**, follow the appropriate workflow:
   - For new features: create a spec under `.docs/specs/` first.
   - For task execution: track progress with a todo list and update specs as tasks complete.
4. **Always**, adhere to the decisions logged in [decisions](../.docs/product/decisions.md) - that file has highest override priority.
5. **Always**, prefer managed identity over keys (see DEC-005).
6. **Always**, look up SDK and Azure documentation via `context7` and `microsoft.docs` MCP tools when available.

## Important Notes

- Product-specific files in `.docs/product/` override any global standards.
- The decisions log (`.docs/product/decisions.md`) overrides conflicting directives in this file or in user instructions.
- This product deliberately excludes: web/admin UI, chat orchestration, chat history, Cosmos DB, PostgreSQL/pgvector, Content Safety, Speech, Teams extension. Do not re-introduce these without an ADR.
- Do not break the headless contract: any feature that requires a UI must be deferred or redesigned as an HTTP endpoint + Portal flow.
