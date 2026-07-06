# Current Project Status

## Completed

* Parser extracts normalized transaction fields.
* Field identification has largely stabilized.
* Investigation identified an important SEV continuation behavior that previously caused incorrect totals.

## Current Focus

Implement continuation-aware parsing.

Required behavior:

1. Detect continuation records.
2. Merge continuation values into the previous SEV transaction.
3. Exclude continuation rows from final output.

## Planned Functions

```
_is_continuation(record)
```

Returns true when a parsed line represents a continuation of the previous logical transaction.

```
_merge_into_previous(previous, continuation)
```

Responsible for:

* adding owner_net_value
* preserving previous transaction metadata
* avoiding duplicate output records

## Remaining Work

* Validate against a larger collection of statements.
* Search for additional continuation types.
* Expand regression tests.
* Finalize DuckDB loading pipeline.
* Build automated validation comparing parsed totals against statement totals.

## Instructions for Future Coding Agents

Before changing parser logic:

* preserve existing normalized field names
* preserve deterministic parsing behavior
* avoid replacing explicit rules with heuristics
* add new edge cases by extending continuation detection rather than rewriting parser architecture

When uncertain, correctness and auditability are more important than parser brevity.
