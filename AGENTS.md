# Branch and PR Workflow

- Never commit or push directly to `dev` or `main`.
- Before editing files, create a task branch from the latest `origin/dev`.
- Use branch names such as `feat/<topic>`, `fix/<topic>`, or `docs/<topic>`.
- After completing the requested changes and relevant checks, commit,
  push the task branch, and create a PR targeting `dev`.
- Before creating a PR, read `.github/pull_request_template.md`.
- Write commit messages and PR titles in English.
- Write PR bodies in Korean, preserving all template headings and checklists.
- Mark checks complete only when actually verified.
- Include only changes belonging to the task.
- Do not merge the PR unless explicitly requested.
