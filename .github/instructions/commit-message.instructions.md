---
description: Conventional Commits specification for commit messages
---
# Summary
The Conventional Commits specification is a lightweight convention on top of commit messages. It provides an easy set of rules for creating an explicit commit history; which makes it easier to write automated tools on top of. This convention dovetails with SemVer, by describing the features, fixes, and breaking changes made in commit messages.

The commit message should be structured as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The commit contains the following structural elements:

1. **fix**: a commit of the type `fix` patches a bug in your codebase (correlates with `PATCH` in SemVer).
2. **feat**: a commit of the type `feat` introduces a new feature to the codebase (correlates with `MINOR` in SemVer).
3. **BREAKING CHANGE**: a commit that has a footer `BREAKING CHANGE:`, or appends a `!` after the type/scope, introduces a breaking API change (correlates with `MAJOR` in SemVer).
4. Other types: `build:`, `chore:`, `ci:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`.
5. Footers may follow a convention similar to git trailer format.

A scope MAY be provided after a type and MUST be a noun describing a section of the codebase surrounded by parentheses, e.g., `fix(parser):`.

## Examples

Commit with description and breaking change footer:
```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

Commit with `!` to draw attention to breaking change:
```
feat!: send an email to the customer when a product is shipped
```

Commit with scope and `!`:
```
feat(api)!: send an email to the customer when a product is shipped
```

Commit with no body:
```
docs: correct spelling of CHANGELOG
```

Commit with scope:
```
feat(lang): add Polish language
```

Commit with multi-paragraph body and multiple footers:
```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

## Repository conventions for doc-ingest-pipeline

- Use `feat(ingest):`, `feat(infra):`, `feat(ci):`, `fix(ingest):`, etc. as common scopes.
- When porting code from the parent accelerator, include the upstream commit SHA in the body, e.g. `Ports code from Azure-Samples/chat-with-your-data-solution-accelerator@5c99c241`.
- Always reference the spec ID in the body for spec-driven work, e.g. `Refs: spec 0001`.
