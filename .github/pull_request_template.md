## Summary

## Validation

- [ ] `python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests`
- [ ] `python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v`
- [ ] JSON manifests validated
- [ ] No live evidence, secrets, or generated output committed

## Safety

- [ ] Collectors remain read-only
- [ ] Sensitive data handling considered
