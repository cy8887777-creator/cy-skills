# Requirements Repository Schema

Read this reference whenever initializing, resuming, or materially updating a
requirements repository. Resolve repository mode first; a governed host project
must not receive a parallel standalone repository.

## Governed project mode

When both `project.config.json` and `docs/governance/source-of-truth.md` exist,
read the governance document and use its declared paths. The standard
`bootstrap-php-uniapp-project` mapping is:

```text
project.config.json                       # identity, targets, directories, project status
docs/
├── requirements/
│   ├── product.md                    # actors, behavior, rules, flows, exceptions, acceptance
│   ├── confirmed-decisions.md        # confirmed/rejected/deferred/open decisions
│   ├── change-log.md
│   └── source-analysis/
│       └── lanhu/
└── acceptance/
    └── acceptance-baseline.json      # feature IDs, scope, status and evidence
```

Do not create top-level `requirements/` or a second `MASTER_REQUIREMENTS.md` in
this mode. Keep project identity and delivery targets in `project.config.json`,
product behavior in `product.md`, decision facts in `confirmed-decisions.md`,
and feature IDs, scope and lifecycle facts in the acceptance baseline. These
files form the governed requirements model with one authority per fact type.
Update cross-references atomically and verify every changed file.

## Standalone mode

When no governed project markers exist, maintain:

```text
requirements/
├── 00-project-overview.md
├── 01-roles-permissions.md
├── 02-functional-requirements.md
├── 03-business-rules.md
├── 04-workflows.md
├── 05-edge-cases.md
├── 06-decisions-rejected.md
├── 07-open-questions.md
├── 08-change-log.md
└── MASTER_REQUIREMENTS.md
```

Do not overwrite customer source files. Original Excel, Word, designs, prototypes, and other supplied materials remain read-only unless the user explicitly asks to modify them.

## Stable IDs

Use uppercase, meaningful domain codes:

- Functional: `FR-<DOMAIN>-001`
- Business rule: `BR-<DOMAIN>-001`
- Permission: `PERM-<DOMAIN>-001`
- Workflow: `WF-<DOMAIN>-001`
- Edge case: `EDGE-<DOMAIN>-001`
- Non-functional: `NFR-<DOMAIN>-001`

Examples: `FR-ORDER-001`, `BR-ORDER-001`, `PERM-MERCHANT-001`, `WF-REFUND-001`, `EDGE-PAYMENT-001`.

Once assigned, IDs remain stable. Never reuse the ID of a removed requirement; retain the item with `REJECTED`, `DEFERRED`, or `OUT_OF_SCOPE` status.

## File responsibilities

The responsibilities below describe the standalone detail files. In governed
mode, persist overview, role, functional, rule, workflow and edge-case facts as
sections of the canonical `product.md`; persist decisions and open questions in
`confirmed-decisions.md`; persist changes in `change-log.md`.

### `00-project-overview.md`

Maintain project background, goals, target users, platform types, complete scope, Phase 1, later phases, explicit exclusions, external systems, major assumptions, global constraints, and source inventory.

### `01-roles-permissions.md`

Maintain actors, users, roles, hierarchy, operation permissions, data permissions, organization and department relationships, ownership, administrator scope, visibility, approval authority, and exceptions.

Never record only “管理员可以管理”. Record what operation the role may perform and which data it may access.

### `02-functional-requirements.md`

Organize by:

```text
端 -> 一级模块 -> 二级模块 -> 功能
```

Decompose vague labels such as “订单管理” into quotable and testable operations such as list, search, filter, detail, accept, reject, ship, cancel, refund, and export.

For each important function, record when known: ID, status, provenance/source, phase, client/platform, actor, description, preconditions, trigger, main flow, rules, operation permission, data scope, key fields, validation, state changes, notifications, exceptions, dependencies, and acceptance criteria. Leave unknown fields `OPEN`; do not invent values for completeness.

### `03-business-rules.md`

Record material pricing, inventory, commission, refund, coupon, membership, settlement, withdrawal, approval, timeout, eligibility, and calculation rules separately, using BR IDs where useful.

### `04-workflows.md`

Record important end-to-end flows such as registration, authentication, purchase, payment, fulfillment, cancellation, after-sales, refund, settlement, withdrawal, approval, and dispute. For stateful objects, explicitly record normal, exceptional, reverse, and invalid transitions.

### `05-edge-cases.md`

Preserve timeout, duplicate submission, concurrency, repeated payment, inventory race, delayed callback, refund or third-party failure, invalid state changes, expiration, deleted records, network interruption, duplicate data, abnormal cancellation/approval, and permission boundaries.

### `06-decisions-rejected.md`

Record accepted major decisions, alternatives considered, rejected options, rejection reason, and impact. Do not delete rejected decisions.

Example:

```text
Decision: 一期采用人工审核退款。
Rejected: 自动退款。
Reason: 客户希望一期保留人工风控。
```

### `07-open-questions.md`

For each unresolved item, record when useful: question, affected module, priority, blocking status, related IDs, current recommendation, and current assumption.

When resolved, update canonical requirement files, explicitly mark or remove the open question, and record meaningful changes. Never silently resolve an `OPEN` item.

### `08-change-log.md`

Log meaningful changes to scope, workflow, permission, rule, phase, functional behavior, important fields, or acceptance conditions. Include affected IDs, old value, new value, reason, source, and date when available. Do not log trivial wording edits.

### Canonical requirements model

Use the governed authoritative source set described above or standalone
`requirements/MASTER_REQUIREMENTS.md` as final-deliverable input. The model
contains overview, scope, phases, actors, permissions, data permissions, module
tree, functions, rules, workflows, states, exceptions, integrations,
non-functional requirements, acceptance criteria, rejected/out-of-scope items,
open questions, and stable IDs without duplicating governed facts.

## Initialization and resume

Run `scripts/init_requirements.py --project-root <root>` before the first
interview question. It auto-detects mode, creates only missing files with
exclusive creation, and prints every resolved authoritative path. Read back the
reported files after creation.

When the resolved repository exists:

1. Never run a destructive reset.
2. The initializer may be run safely because it skips existing files, but reading persisted state comes first.
3. Always read the resolved decision/open-question register and canonical requirements file when present.
4. Reconstruct the current branch before asking anything.

Do not create a repository merely while installing or validating this Skill.
Create it only after explicit invocation for a project discovery task. In
governed mode, never create top-level `requirements/`.

## Integrity rules

- Use the resolved governed sources as the update surface in governed mode. In
  standalone mode, use canonical detail files during discovery and
  `MASTER_REQUIREMENTS.md` as the normalized final model.
- Keep provenance distinct from lifecycle status; a `SOURCE_DOCUMENT` fact may still be `OPEN` when approved sources conflict.
- Use one consistent domain code and term for the same concept.
- If a new answer contradicts a persisted fact, preserve both evidence records and include a concise conflict-resolution question in the next valid round.
- Update all affected cross-references atomically, then read them back before continuing.
