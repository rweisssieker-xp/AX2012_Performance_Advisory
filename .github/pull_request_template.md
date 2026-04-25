## Summary

Describe the user-facing change and why it is needed.

## Validation

- [ ] `python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests`
- [ ] `python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v`
- [ ] JSON manifests validated
- [ ] Skill frontmatter validated
- [ ] Dashboard generated or smoke-tested when UI/reporting changed
- [ ] No live evidence, secrets, or generated output committed

## Safety

- [ ] Collectors remain read-only
- [ ] Sensitive data handling considered
- [ ] Admin/remediation behavior is gated by approval, validation, and rollback notes

## Documentation

- [ ] README/docs updated for user-facing changes
- [ ] New scripts listed in `plugins/ax-performance-advisor-plugin/scripts/README.md`
- [ ] New skills include `SKILL.md` frontmatter and safety notes
