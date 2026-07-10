# Token cost and guardrails

Auto mode performs model inference for every position and challenge, so
it costs more than a single chat completion. Ploidy exposes limits that
bound this cost without changing the same-model intervention.

## What one auto debate calls

For `deep_n=1` and `fresh_n=1`, auto mode generates:

1. one Deep position with non-empty `context_documents`;
2. one Fresh position without those documents;
3. one Deep-owned challenge;
4. one Fresh-owned challenge; and
5. optionally, one LLM convergence meta-analysis when
   `PLOIDY_LLM_CONVERGENCE=1`.

Input cost depends primarily on the supplied Deep context and the
backend's prompt-caching policy. Output cost depends on `effort`. Consult
the configured provider's current pricing instead of relying on a fixed
dollar estimate in this documentation.

## Keep the model fixed across sides

Ploidy isolates context as the independent variable. `deep_model` and
`fresh_model` exist for controlled cross-model experiments and backend
routing diagnostics, but a valid Ploidy service debate sets both to the
same model (or leaves both unset so they inherit the same backend
default).

Using a stronger Deep model and a cheaper Fresh model may reduce spend,
but it confounds model and context. Such a run must be labelled a
heterogeneous-model control, not evidence for Ploidy's context-asymmetry
mechanism.

## Guardrails that preserve the intervention

### Context ceiling

`PLOIDY_MAX_CONTEXT_TOKENS` rejects a run whose combined
`context_documents` exceed the approximate ceiling. It is a spend
guardrail, not silent truncation. Hosted examples set it to `20000`.

`PLOIDY_MAX_CONTEXT_DOCS` separately limits document count.

### Effort

`effort` controls the per-call output ceiling:

| effort | Maximum output tokens per call |
|---|---:|
| `low` | 1024 |
| `medium` | 2048 |
| `high` | 4096 |
| `max` | 8192 |

Lower effort reduces maximum output size for both sides equally and
therefore preserves the same-model comparison.

### Ploidy level

`deep_n` and `fresh_n` are active seats inside one debate. Increasing
them adds independently generated positions and challenges; it is not a
free repetition counter. Keep `1n` for the smallest service call and use
higher levels only when the decision justifies the additional inference.

### Rate and retention limits

`PLOIDY_RATE_CAPACITY` is the per-tenant burst allowance and
`PLOIDY_RATE_PER_SEC` is the sustained rate. Hosted examples use `20`
and `1` respectively.

These limits are not an admission system. In v0.4.0 OAuth mode,
unrestricted DCR can mint new client IDs and reset per-client buckets.
Use a gateway or controlled static bearer identities for abuse control.

`PLOIDY_RETENTION_DAYS` bounds stored completed/cancelled debate history;
it does not change inference cost but prevents unbounded local storage.

## Prompt caching

`PLOIDY_API_CACHE=1` enables the explicit cache-control path for supported
Anthropic-compatible endpoints. Other backends may apply their own
prefix caching. Cache availability and discounts are provider contracts,
so verify them against the configured endpoint before including savings
in a budget.

## Solo mode

`debate(mode="solo")` makes no position or challenge generation calls;
the caller supplies those texts. Rule-based convergence also makes no
model call. Enabling `PLOIDY_LLM_CONVERGENCE=1` adds the optional
meta-analysis inference.

The caller must still create the Fresh position in an independent clean
context. Reusing one anchored conversation is cheaper, but it is not the
same intervention.

## Hosted baseline

```bash
PLOIDY_MAX_CONTEXT_DOCS=10
PLOIDY_MAX_CONTEXT_TOKENS=20000
PLOIDY_RATE_CAPACITY=20
PLOIDY_RATE_PER_SEC=1
PLOIDY_RETENTION_DAYS=30
```

Track actual input/output tokens and provider invoices for your workload;
do not infer production cost from research-run counts.
