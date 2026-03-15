# API Reference

Ploidy exposes six MCP tools for debate orchestration. All tools are available over the Streamable HTTP transport at `http://localhost:8765/mcp`.

## Tools Overview

| Tool | Purpose | Read-only | Destructive | Idempotent |
|------|---------|:---------:|:-----------:|:----------:|
| `debate_start` | Create a new debate | No | Yes | No |
| `debate_position` | Submit a position statement | No | No | No |
| `debate_challenge` | Submit a challenge to another position | No | No | No |
| `debate_converge` | Trigger convergence analysis | No | No | No |
| `debate_status` | Get current debate state | Yes | No | Yes |
| `debate_history` | List past debates | Yes | No | Yes |

---

## debate_start

Begin a new debate session with a decision prompt. Creates a debate record and its session group (Deep + Fresh).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `prompt` | `string` | Yes | The decision question to debate. |
| `context_documents` | `list[string]` | No | Optional documents to provide to the Deep session. These are stored for the record but NOT shown to the Fresh session. |

### Returns

```json
{
  "debate_id": "debate-a1b2c3d4",
  "experienced_session_id": "debate-a1b2c3d4-exp8f2a",
  "fresh_session_id": "debate-a1b2c3d4-fre3b7c",
  "phase": "independent",
  "prompt": "Should we use monorepo or polyrepo?"
}
```

### Annotations

- `destructiveHint: true` -- Creates a new debate record
- `readOnlyHint: false`
- `idempotentHint: false` -- Each call creates a new debate

### Example

```
User: Use debate_start to debate "Should we migrate our REST API to GraphQL?"

Tool call: debate_start(
  prompt="Should we migrate our REST API to GraphQL?",
  context_documents=["We have 47 REST endpoints serving 3 mobile clients and 1 web app."]
)
```

---

## debate_position

Submit a position from a session. Records a session's stance on the debate prompt during the POSITION phase.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `session_id` | `string` | Yes | The session submitting the position. |
| `content` | `string` | Yes | The position statement. Should be specific and actionable. |

### Returns

```json
{
  "session_id": "debate-a1b2c3d4-exp8f2a",
  "phase": "position",
  "status": "recorded",
  "content_length": 342
}
```

### Annotations

- `destructiveHint: false`
- `readOnlyHint: false`
- `idempotentHint: false` -- Each submission is recorded as a new message

### Example

```
Tool call: debate_position(
  session_id="debate-a1b2c3d4-exp8f2a",
  content="We should keep REST. Our 47 endpoints are well-documented, our mobile team
           knows the patterns, and the migration cost outweighs the benefits for our
           current team size of 4 engineers."
)
```

---

## debate_challenge

Submit a challenge to another session's position. Records a session's critique during the CHALLENGE phase.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `session_id` | `string` | Yes | The session submitting the challenge. |
| `content` | `string` | Yes | The challenge or critique text. |
| `action` | `string` | No | Semantic action classifying this message's intent. Default: `"challenge"`. |

### Semantic Actions

| Action | Meaning |
|--------|---------|
| `agree` | "I reached the same conclusion independently." |
| `challenge` | "I disagree with this position, here's why." |
| `propose_alternative` | "Neither position is right -- consider this third option." |
| `synthesize` | "Both positions have merit -- here's a synthesis." |

### Returns

```json
{
  "session_id": "debate-a1b2c3d4-fre3b7c",
  "phase": "challenge",
  "action": "challenge",
  "status": "recorded",
  "content_length": 289
}
```

### Annotations

- `destructiveHint: false`
- `readOnlyHint: false`
- `idempotentHint: false`

### Example

```
Tool call: debate_challenge(
  session_id="debate-a1b2c3d4-fre3b7c",
  content="The 'well-documented' claim assumes documentation stays current.
           GraphQL's self-documenting schema eliminates this maintenance burden.
           Also, 3 mobile clients making different data requests is exactly the
           over-fetching problem GraphQL solves.",
  action="challenge"
)
```

---

## debate_converge

Trigger convergence analysis for a debate. Runs the convergence engine on the debate transcript and produces a structured synthesis of agreements and disagreements.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `debate_id` | `string` | Yes | The debate to analyze. |

### Returns

```json
{
  "debate_id": "debate-a1b2c3d4",
  "synthesis": "Keep REST for existing endpoints. Introduce GraphQL as a new
                gateway layer for mobile clients, allowing gradual migration
                without disrupting the current API.",
  "confidence": 0.72,
  "points": [
    {
      "category": "agreement",
      "summary": "Migration cost is non-trivial",
      "session_a_view": "47 endpoints is too many to migrate at once",
      "session_b_view": "Full migration would be costly regardless of endpoint count",
      "resolution": "Both agree migration should be incremental if done at all"
    },
    {
      "category": "productive_disagreement",
      "summary": "Documentation maintenance burden",
      "session_a_view": "REST endpoints are well-documented",
      "session_b_view": "Documentation requires ongoing maintenance; schemas are self-documenting",
      "resolution": "Valid concern -- GraphQL schema as documentation source of truth"
    }
  ]
}
```

### Annotations

- `destructiveHint: false`
- `readOnlyHint: false`
- `idempotentHint: false`
- `openWorldHint: false` -- Analysis is based only on the debate transcript

### Example

```
Tool call: debate_converge(
  debate_id="debate-a1b2c3d4"
)
```

---

## debate_status

Get current state of a debate. Returns phase, session info, and message counts.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `debate_id` | `string` | Yes | The debate to inspect. |

### Returns

```json
{
  "debate_id": "debate-a1b2c3d4",
  "phase": "challenge",
  "message_count": 4,
  "sessions": [
    {
      "session_id": "debate-a1b2c3d4-exp8f2a",
      "role": "experienced",
      "messages_submitted": 2
    },
    {
      "session_id": "debate-a1b2c3d4-fre3b7c",
      "role": "fresh",
      "messages_submitted": 2
    }
  ]
}
```

### Annotations

- `readOnlyHint: true` -- Does not modify debate state
- `destructiveHint: false`
- `idempotentHint: true` -- Same input always returns current state

---

## debate_history

Retrieve past debates and their outcomes. Lists recent debates with their status and convergence results.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `limit` | `integer` | No | Maximum number of debates to return. Default: `50`. |

### Returns

```json
{
  "debates": [
    {
      "id": "debate-a1b2c3d4",
      "prompt": "Should we migrate our REST API to GraphQL?",
      "status": "complete",
      "created_at": "2026-03-15T14:30:00",
      "updated_at": "2026-03-15T14:35:22"
    }
  ],
  "total": 1,
  "limit": 50
}
```

### Annotations

- `readOnlyHint: true`
- `destructiveHint: false`
- `idempotentHint: true`

---

## Data Types

### DebatePhase

The debate protocol progresses through five phases:

| Phase | Description |
|-------|-------------|
| `independent` | Sessions analyze the prompt independently |
| `position` | Sessions declare their stances |
| `challenge` | Sessions critique each other's positions |
| `convergence` | Convergence engine synthesizes the debate |
| `complete` | Debate concluded, result available |

### SemanticAction

Actions that classify the intent of a challenge message:

| Action | Description |
|--------|-------------|
| `agree` | Independent agreement with the other position |
| `challenge` | Disagreement with specific reasoning |
| `propose_alternative` | Neither position is adequate; a third option is proposed |
| `synthesize` | Both positions have merit; a synthesis is offered |

### ConvergencePoint

A single point in the convergence analysis:

| Field | Type | Description |
|-------|------|-------------|
| `category` | `string` | One of `agreement`, `productive_disagreement`, `irreducible` |
| `summary` | `string` | Brief description of the point |
| `session_a_view` | `string` | The Deep session's perspective |
| `session_b_view` | `string` | The Fresh session's perspective |
| `resolution` | `string \| null` | Synthesized resolution, if any |
