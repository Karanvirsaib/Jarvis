---
name: task-automation
description: Design and operate bounded local or browser automations with visible scope, checkpoints, and safe recovery.
---

# Task automation

1. Identify the trigger, inputs, allowed scope, expected output, time limit, and completion check. Prefer a small reversible run first.
2. For file or desktop changes, list the exact target paths and preserve originals or create backups when practical. Never recursively modify broad directories based only on a fuzzy name match.
3. For browser and account tasks, inspect before changing. Keep a record of completed steps and evidence; do not equate a click with a successful outcome.
4. Ask before external side effects such as sending, submitting, publishing, buying, deleting, or changing permissions. Show the exact final content or change before approval.
5. Bound retries and execution time. After one materially different recovery attempt, stop and explain the error, partial work, and safe workaround.
6. On completion, report what changed, what was verified, what remains, and any scheduled/background process that is still active.
