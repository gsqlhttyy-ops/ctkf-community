# Community Architecture

CTKF Community is deliberately isolated from the private CTKF engineering and
Pro codebases.

```text
requirement document
  -> immutable normalized source + hashes
  -> section inventory + high-impact question gate
  -> authoritative 19-stage delivery mainline
  -> 57-task atomic backlog
  -> IDE-specific RUNBOOK.md
  -> local integrity verification
```

The package uses only the Python standard library. It does not contain payment,
license issuance, customer ledgers, production credentials, private templates,
advanced Agent runtime code, or Git history from the engineering repository.

Generated applications are separate works. The Apache-2.0 license applies to
CTKF Community source distributed here; users remain responsible for choosing
and documenting the license of their generated application and its dependencies.
