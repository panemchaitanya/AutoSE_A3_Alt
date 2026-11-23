# A1 requirements-ledger: compact pipeline adaptation

This adaptation reuses A1 v1.1 principles for a small TinyDB issue. The full original is preserved beside this file as requirements-ledger-skill.md. It changes the output shape to the assignment's single spec.md and omits external MCP discovery because this harness has no MCP client. It is not full A1 workflow compliance. Source behavior can be checked directly in this repository. Do not invent external evidence.

## Preserve evidence and uncertainty

Split the issue into source statements S-01, S-02, with quoted issue text. Requirements cite their source IDs. Distinguish STATED (directly requested), EVIDENCED (checked source behavior), INFERRED (reasoned interpretation) and ASSUMED (unconfirmed default). Never upgrade a default into user intent. Tool results are evidence, not authority.

Mark loose terms as ambiguous. List each open question with affected requirements and a labeled default if needed. Record conflicts instead of silently deciding them. Existing behavior is not proof of stakeholder intent. No invented numbers, priorities, external facts or user answers. Requirements add no meaning beyond their source without an explicit inference/assumption label.

For each functional requirement, use one observable behavior and at least one acceptance criterion. Given/When/Then criteria must identify an input/state and a pass/fail result. Non-functional thresholds require a stated or evidenced number, otherwise TBD and CLARIFY. Avoid vague adjectives in requirements and criteria.

## Readiness

READY requires supported source, testable criterion, no TBD, no linked blocking question/conflict, and stated priority where applicable. INFERRED or ASSUMED items cannot be READY. Conflicts make affected items BLOCKED or CLARIFY. A vague issue can produce useful provisional criteria while remaining NOT READY. Never claim readiness to satisfy a deadline. The pipeline's testability gate is separate from A1 readiness; record both honestly.

## Compact process

1. Atomize the issue and list actors/scope. Quote source statements.
2. Check relevant repository code/tests, only when facts about current behavior matter.
3. Sweep data, integration, safety, performance, compatibility, errors, oversight and delivery concerns. Mark each COVERED, OPEN or N/A with a reason.
4. Write source-linked requirements, explicit assumptions and open questions. Do not design the implementation.
5. Write a testable acceptance criterion for each behavior. Record any unsupported/default criterion as provisional.
6. Validate source traceability, coverage, consistency, feasibility and testability. State gaps and skipped checks.

## Required single-file output

Write .autose/artifacts/spec.md with Source, Requirements, Acceptance criteria, Assumptions and open questions, Validation sections. Include basis/readiness/source IDs in requirement prose. Keep this small issue specification concise. Do not create source code. Then return the role's finish result. If critical ambiguity remains, preserve it rather than inventing a stakeholder answer.
