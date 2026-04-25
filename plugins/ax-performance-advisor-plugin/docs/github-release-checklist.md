# GitHub Release Checklist

Use this checklist before opening a public PR or creating a release.

## Repository Hygiene

- [ ] No live evidence committed.
- [ ] No generated `out/` files committed unless they are intentional static examples.
- [ ] No credentials, PATs, Power BI endpoints, Jira tokens, or connection strings with passwords.
- [ ] `.gitignore` covers local evidence, generated dashboards, caches, logs, and virtual environments.

## Validation

- [ ] `python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests`
- [ ] `python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v`
- [ ] JSON manifests validate with `python -m json.tool`.
- [ ] Skill frontmatter validates.
- [ ] Dashboard smoke test passes.

## Documentation

- [ ] Root `README.md` updated.
- [ ] `docs/INDEX.md` links new docs.
- [ ] `scripts/README.md` documents new scripts.
- [ ] New user-facing features include docs and tests.
- [ ] Security or data-handling impact documented.

## Release Notes

Include:

- main features
- safety model changes
- new scripts or skills
- breaking changes
- known limitations
- validation evidence
