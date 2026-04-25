---
name: admin-execution-mode
description: Generate guarded admin execution previews with policy gates, confirmation tokens, audit records, and rollback/validation metadata.
---

# Admin Execution Mode

Run `scripts/admin_execution.py`. Never claim the dashboard executes PROD changes. Treat generated SQL as preview scripts requiring admin review, approval reference, confirmation token, rollback, and post-change validation.
