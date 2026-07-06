# GitHub Knowledge Base

## OVERVIEW

Repository collaboration metadata: PR template plus issue forms.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| PR body | `pull_request_template.md` | Preserve headings and checklist shape. |
| Issue forms | `ISSUE_TEMPLATE/` | Bug/feature forms and chooser config. |

## CONVENTIONS

- Issue and PR titles are written in English.
- Commit messages are written in English and follow the repository's conventional style, for example `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`, or `refactor: ...`.
- Issue and PR bodies are written in Korean while preserving the template's original headings and checklist shape.
- Issue bodies follow the selected issue form sections. Feature issues use `Summary`, `Goal`, `Scope`, and `Acceptance Criteria`; bug issues use `Summary`, `Current Behavior`, `Expected Behavior`, `Steps To Reproduce`, and `Acceptance Criteria`.
- Keep PR bodies aligned with `pull_request_template.md`, even when writing the content in Korean.
- Required PR sections are `What`, `How To Test`, `Review Focus`, `Screenshots / Logs`, and `Related`.

## ANTI-PATTERNS

- Do not translate issue titles, PR titles, commit subjects, or template headings to Korean.
- Do not remove template headings just because a section is short; mark non-applicable sections explicitly.
