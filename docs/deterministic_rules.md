# Deterministic Rules for Email Triage

## Overview

The deterministic rules engine provides a configurable set of checks that run before the LLM classification step. Each rule:

- Evaluates a set of AND/OR/NOT conditions across headers, body text, recipients, existing Gmail labels, and any labels already decided during this run.
- Can **add** labels immediately, **exclude** labels so the LLM cannot apply them later, and optionally **terminate** processing to skip the LLM entirely.
- Runs in the order it appears in the configuration file, with later rules allowed to override earlier ones (an override is logged at INFO level).

At the end of rule and LLM processing, the workflow applies every label currently marked “add,” skips any already present in Gmail, and records all applied labels in the run statistics and verbose output.

## Configuration

1. Copy `config/deterministic_rules.example.yaml` to `config/deterministic_rules.yaml` (this path can be overridden with the `DETERMINISTIC_RULES_FILE` environment variable).
2. Edit the file to define an ordered `rules:` list. Each rule supports:
   - `name` (required) and optional `description`.
   - `when`: condition tree with `all`, `any`, or `not` blocks plus field-specific matchers (e.g., `sender`, `subject`, `body`, `recipients`, `existing_labels`, `decided_labels`, `excluded_labels`).
   - `actions`: `add` and `exclude` arrays referencing labels defined in `config/labels.json`.
   - `terminate`: when `true`, label actions are applied and the workflow skips any remaining deterministic rules and the LLM.
3. Keep the example file handy as a reference for condition syntax (case-insensitive substring matching, recipient-count checks, internal/external classifications, etc.).
4. All referenced labels must exist in `config/labels.json`; the workflow raises a descriptive error if a rule mentions an undefined label.

## Design Rationale

- **Deterministic first, probabilistic second**: Fast, low-risk decisions (VIP senders, mailing lists, automated acknowledgments) should never wait for an LLM classification. Running these rules first keeps the triage predictable.
- **Ordered overrides**: Admins reason about rules sequentially, so later rules can intentionally override earlier decisions. Logging overrides at INFO makes it obvious when a later rule changed course.
- **Add *and* exclude**: We frequently know that a label is inappropriate even before seeing the LLM output (e.g., newsletters should never be `response-required`). Tracking exclusions lets the workflow ignore an LLM choice without error.
- **Termination option**: Some emails don’t need the LLM at all—termination saves latency and avoids irrelevant completions while still applying any deterministic labels chosen so far.
- **YAML config**: YAML’s readability and comment support make it easy for non-developers to edit rules. Using the same pattern as other configs (`LABEL_CONFIG_FILE` etc.) keeps deployments consistent.

## Future Enhancements

- **Additional data sources**: Expose message metadata such as received timestamps, attachment presence, Gmail category hints, and thread statistics for richer conditions.
- **Reusable condition snippets**: Allow named predicates (macros) to reduce repetition when the same sender/recipient logic is reused across multiple rules.
- **Regex and advanced text matching**: Add optional regex support or fuzzy matching for subject/body conditions when substring checks are not sufficient.
- **Rule testing utilities**: Provide a CLI helper that runs sample messages against the deterministic rules to preview actions without calling Gmail or the LLM.
