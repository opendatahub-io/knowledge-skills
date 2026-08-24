# Examples Page Guidance

Each page in `examples/` shows real incidents for one failure class:
which report hit it, what failed, and how it was fixed (MR link and the
relevant diff).

Show only the most useful examples: clearest error, cleanest fix, or a distinct
approach. Drop or replace entries that add nothing new.

## Page structure

- **Title** — the failure class
- **Symptom** — one-liner (error message or log pattern)
- **Incidents** — a small set of entries: report id, Jira key, what happened,
  fix MR, trimmed diff

## When to update vs create

- **Update** if an existing page covers this failure class. Add or replace an
  incident only when this report is more useful or shows a different fix.
- **Create** only for a genuinely new class.

## Naming

Lowercase kebab-case: `examples/<short-slug>.md`. No ID prefixes.

## Catalog

`examples/README.md` lists every page:

```markdown
| Example | Description |
|---------|-------------|
| [cuda-version-pin.md](cuda-version-pin.md) | CI pins wrong CUDA version |
| [missing-build-dep.md](missing-build-dep.md) | Build fails on missing system library |
```
