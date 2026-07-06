# Known Parsing Edge Cases

## SEV Continuation Transactions

Important discovery:

A `SEV` tax deduction line may be followed by one or more transaction lines that visually appear independent but are actually continuations.

Typical continuation records include:

* `TRN`
* `MIS`

These continuation lines:

* have no meaningful `interest_type`
* belong to the preceding `SEV` transaction
* should not become independent output records

## Merge Rule

Continuation records should be merged into the previous SEV record.

Specifically:

* add the continuation `owner_net_value`
* preserve the original SEV record
* suppress the continuation record from final output

## Continuation Detection

Current understanding:

A continuation record satisfies approximately:

```
line_type == "TRN" (or "MIS")
AND
interest_type is None
```

These should trigger merge behavior.

## Parser Helpers

Expected helper functions:

```
_is_continuation(record)

_merge_into_previous(previous, continuation)
```

The continuation detection logic should remain isolated so additional continuation types can be added later.

## Guiding Principle

The statement layout is authoritative.

Visual continuation in the source document outweighs assumptions based solely on transaction type.
