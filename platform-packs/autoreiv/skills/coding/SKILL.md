---
name: Repository Code & Files
description: Repository file reading, directory listing, guarded writes, and patching.
---

# Repository Code & Files

Inspect, analyze, and safely modify source code files within the repository checkout.

## Available Tools

- `repo_file_read`: Read UTF-8 text from files within the checkout.
- `repo_file_list`: Inspect directory trees and file listings.
- `repo_file_write`: Guarded file write or creation (under operator confirmation).
- `repo_file_patch`: Guarded patch to modify existing files.

## Workflow Order

1. Read and inspect existing files using `repo_file_read` and `repo_file_list` before proposing changes.
2. Confirm the exact line ranges and syntax before issuing patches.
3. Review changes before submission.
