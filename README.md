# doc-ingest-pipeline

Headless Azure document ingestion pipeline. Watches a Blob container, parses documents with Azure AI Document Intelligence, chunks and embeds the content, and indexes the result in Azure AI Search. Intended as a reusable foundation for downstream RAG, search, and agent solutions.

This product is **carved out** of [Azure-Samples/chat-with-your-data-solution-accelerator](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator). It reuses that repo's ingestion code while excluding chat, orchestration, chat history, PostgreSQL, Content Safety, Speech, and any UI surface.

## Status

> **Phase 1 / Spec 0001** -- repo scaffolding and Azure Functions entry-point port. The function app starts but does not yet process documents end-to-end. Subsequent specs port the utilities, embedders, search handlers, and Bicep modules.

> **First time in this repo?** Read [HANDOFF.md](HANDOFF.md) before doing anything else. It walks through `poetry install`, lockfile generation, local verification, closing out spec 0001, and picking the next spec.

## Documentation

- Product mission: [.docs/product/mission.md](.docs/product/mission.md)
- Tech stack: [.docs/product/tech-stack.md](.docs/product/tech-stack.md)
- Roadmap: [.docs/product/roadmap.md](.docs/product/roadmap.md)
- Decisions log (override authority): [.docs/product/decisions.md](.docs/product/decisions.md)
- Code style: [.docs/standards/code-style.md](.docs/standards/code-style.md)
- Best practices: [.docs/standards/best-practices.md](.docs/standards/best-practices.md)
- Component reuse map (what is copied from the parent and at what SHA): [component-reuse-map.md](component-reuse-map.md)
- Active specs: [.docs/specs/](.docs/specs/)

## Local Development

Prerequisites: Python 3.10+, Poetry, Azure Functions Core Tools (`func`).

```pwsh
poetry install
poetry run pre-commit install
poetry run pytest -q
```

To start the function host locally:

```pwsh
cd src/functions
func host start
```

Per [decisions.md](.docs/product/decisions.md) (DEC-005), service-to-service auth uses Managed Identity. For local development, sign in with `az login` so `DefaultAzureCredential` can acquire tokens.

## License

[MIT](LICENSE.md) -- matches the parent accelerator per DEC-006.
