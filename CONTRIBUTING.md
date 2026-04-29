# Contributing to rag-nano

Thanks for considering a contribution. Please read [`README.md`](README.md) first to understand what this project does and the scope it deliberately stays inside.

## Local setup

```bash
git clone https://github.com/3bluebytes/nanorag
cd nanorag
uv sync
uv run scripts/download_models.sh   # ~2.3 GB, only needed if you ingest real data
uv run pytest                          # all tests use mock backends; no model needed
```

## Before opening a PR

The CI pipeline runs the four checks below. PRs that don't pass them won't merge — running them locally first is the fastest feedback loop:

```bash
uv run ruff check rag_nano tests
uv run ruff format --check rag_nano tests
uv run pyright rag_nano
uv run pytest
```

If `ruff format --check` fails, run `uv run ruff format rag_nano tests` to fix it.

## Commit message conventions

Look at `git log` for examples and match the existing style. The repo currently uses:

- Spec-driven feature work: `[Spec Kit] [US#] Phase N description`
- Documentation: `docs(scope): description`
- Bug fixes: `fix(scope): description`
- Polish / refactors / type-fixes: `[Spec Kit] [Polish] description` or `chore(scope): description`

Keep the subject line under 72 chars; use the body to explain *why*, not *what* (the diff already shows what).

## Filing issues

- **Bug reports** — please include reproduction steps, the command you ran, and what you expected vs. what happened.
- **Feature ideas** — cross-check against [`specs/001-minimal-rag-loop/spec.md`](specs/001-minimal-rag-loop/spec.md) first. v1 is intentionally tight in scope. Anything that grows the librarian's responsibilities (chat history, prompt construction, multi-turn state) belongs in the orchestrator, not here — those are v2+ conversations at best.

## Scope reminder

`rag-nano` is the **librarian** layer: retrieval + provenance only. Prompt construction, dialogue state, short-term memory, and answer generation belong in the agent that calls it. PRs that blur this boundary will likely be redirected.

## Running the smoke

To exercise the full pipeline end-to-end (ingest → serve → retrieve → eval) against the seed corpus, follow the "What v1 done looks like" script in [`specs/001-minimal-rag-loop/quickstart.md`](specs/001-minimal-rag-loop/quickstart.md).
