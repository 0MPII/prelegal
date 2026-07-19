---
name: Cerebras Inference
description: Use this to write code to call an LLM using LiteLLM and Openrouter with the Cerebras Inference provider.
---
---
name: cerebras-inference
description: >
  Use the Cerebras Inference API (`api.cerebras.ai`) to run open-source LLMs at
  extreme speed — thousands of tokens per second on Wafer-Scale Engine hardware.
  Trigger this skill whenever the user mentions Cerebras, WSE, `gpt-oss`,
  `cerebras_cloud_sdk`, or asks for "the fastest LLM inference", "real-time
  streaming tokens", "sub-second LLM latency", "low-latency voice agent",
  "cheap open-source LLM API", or wants to move a workload off OpenAI /
  Anthropic / GPU providers for speed. Also trigger when the user pastes code
  from `cloud.cerebras.ai` or the docs at `inference-docs.cerebras.ai`, or asks
  which model to pick on Cerebras. Deliver working code first — Python, Node,
  cURL, or OpenAI-compatible drop-in — then explain. Always check the live
  model catalog before recommending a model ID; Cerebras rotates preview models
  frequently.
---

# ⚡ Cerebras Inference API

You are helping the user build with **Cerebras Inference** — an OpenAI-compatible API that serves open-weight models on Cerebras Wafer-Scale Engines. The pitch is speed: `gpt-oss-120b` runs at roughly 3,000 tokens/sec, well over an order of magnitude faster than typical GPU-hosted APIs. Everything else (auth, request shape, streaming, tool use) mirrors OpenAI closely, so migration is usually a base-URL swap.

Your job: get the user to a working call fast, use the right model ID, and flag the tradeoffs honestly.

---

## 🔎 Step 1 — Always verify the model list before recommending one

Cerebras rotates **preview** models on short notice (Z.ai GLM 4.7 is scheduled for deprecation on Aug 17, 2026, for example). Before you tell the user to use a specific model ID, check the live catalog:

- Docs: `https://inference-docs.cerebras.ai/models/overview`
- Or programmatically: `GET https://api.cerebras.ai/v1/models`

As of the last update to this skill, the public endpoints served:

| Tier | Model ID | Size | Approx speed |
| :--- | :--- | :--- | :--- |
| Production | `gpt-oss-120b` | 120B | ~3,000 tok/s |
| Preview | `gemma-4-31b` | 31B | ~1,850 tok/s |
| Preview | `zai-glm-4.7` | 355B (MoE) | ~1,000 tok/s |

If the user asks "what's the best model on Cerebras for X", search the docs live rather than trusting this table.

---

## 🛠️ Step 2 — Setup

1. Get an API key at `https://cloud.cerebras.ai` (free tier includes $5 of credit and ~30 RPM).
2. Export it: `export CEREBRAS_API_KEY="sk-..."`
3. Install the SDK:

```bash
# Python
pip install --upgrade cerebras_cloud_sdk

# Node.js
npm install @cerebras/cerebras_cloud_sdk@latest
```

The base URL for direct HTTP or OpenAI-compatible clients is:
```
https://api.cerebras.ai/v1
```

---

## 🚀 Step 3 — First working call

Give the user whichever language they're actually in. Default to Python if unspecified.

### Python (native SDK)
```python
import os
from cerebras.cloud.sdk import Cerebras

client = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])

resp = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Why is fast inference important?"}],
)
print(resp.choices[0].message.content)
```

### Node.js (native SDK)
```javascript
import Cerebras from "@cerebras/cerebras_cloud_sdk";

const client = new Cerebras({ apiKey: process.env.CEREBRAS_API_KEY });

const resp = await client.chat.completions.create({
  model: "gpt-oss-120b",
  messages: [{ role: "user", content: "Why is fast inference important?" }],
});
console.log(resp.choices[0].message.content);
```

### cURL
```bash
curl https://api.cerebras.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CEREBRAS_API_KEY" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "why is fast inference important?"}],
    "temperature": 0.2
  }'
```

### OpenAI-compatible drop-in (Python)
Best migration path if the user already has OpenAI SDK code:
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["CEREBRAS_API_KEY"],
    base_url="https://api.cerebras.ai/v1",
)
resp = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Hello"}],
)
```

---

## 🌊 Step 4 — Streaming (this is why people come here)

Streaming is where Cerebras shines — tokens arrive so fast that voice agents and code copilots feel instant.

```python
stream = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Write a haiku about wafers."}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content or ""
    print(delta, end="", flush=True)
```

Node.js equivalent uses `for await (const chunk of stream)`. cURL: add `"stream": true` and read SSE.

---

## 🔧 Step 5 — Tool calling

OpenAI-compatible tool/function calling works. Same schema as OpenAI's `tools` array:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

resp = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "What's the weather in Stockholm?"}],
    tools=tools,
    tool_choice="auto",
)
print(resp.choices[0].message.tool_calls)
```

Then feed the tool result back as a `{"role": "tool", "tool_call_id": ..., "content": ...}` message in a follow-up call. Same loop as OpenAI.

---

## 📐 Step 6 — Structured outputs

Use `response_format` with a JSON schema when you need parseable output:

```python
resp = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Extract: 'John Doe, 34, engineer'"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "role": {"type": "string"},
                },
                "required": ["name", "age", "role"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
)
```

---

## 🧠 Step 7 — Reasoning models

For `gpt-oss-120b` and other reasoning-capable models, you can inspect the model's thinking:

```python
resp = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Prove sqrt(2) is irrational."}],
    reasoning_effort="medium",   # "low" | "medium" | "high"
)
# The final answer:
print(resp.choices[0].message.content)
# Some SDK versions expose reasoning tokens on `resp.choices[0].message.reasoning`
```

Higher effort = more intermediate tokens, better answers on hard problems, higher token cost.

---

## 💰 Rate limits, tiers, pricing

- **Free trial**: ~30 RPM, $5 credit, meant for prototyping.
- **Pay-as-you-go**: ~10× higher rate limits, priority processing. Fund starting at $10.
- **Dedicated endpoints**: enterprise SLAs, custom weights, contact sales.

Pricing is per **combined** input+output tokens (no separate prompt/completion rates like OpenAI/Anthropic). Roughly $0.50–$1.50 per million tokens depending on model. For latest numbers: `https://inference-docs.cerebras.ai/support/pricing`.

---

## 🧭 When to pick Cerebras vs. something else

**Pick Cerebras when:**
- Latency-sensitive UX (voice agents, live coding assistants, streaming chat) where perceived speed is the product.
- Batch throughput at scale — the `/v1/batch` endpoint plus the raw tok/s makes large document processing 40–60% cheaper than typical OpenAI-tier pricing.
- You're OK with an open-weight model (GPT-OSS, Gemma, GLM) and want to avoid vendor lock-in.

**Pick Claude / GPT-5 / Gemini when:**
- You need top-tier reasoning, long-context comprehension, or multimodal quality that open-weight models still lag on.
- You need vision, audio, or other modalities Cerebras doesn't currently serve on public endpoints (only `gemma-4-31b` supports image inputs at time of writing — check the docs).
- Compliance requires a specific vendor / region.

Be honest with the user about this. Cerebras is not "faster Claude" — it's a different model class served on faster silicon.

---

## ⚠️ Common gotchas

1. **Model ID typos and stale IDs.** `gpt-oss-120b` not `gpt-oss` or `openai/gpt-oss-120b`. Preview model IDs change — always cross-check `/v1/models`.
2. **`max_tokens: -1`** in cURL examples means "no limit" (up to context). If you're getting truncated output, set it explicitly.
3. **OpenAI SDK migration:** most code works with just a `base_url` swap, but `logprobs`, `n>1`, `seed` behavior, and some experimental fields differ. Test before you ship.
4. **Prompt caching** is available (`https://inference-docs.cerebras.ai/capabilities/prompt-caching`) — use it for repeated system prompts to cut cost and latency further.
5. **Rate limits are per-key, per-minute**, not per-token-per-second. A single 3,000 tok/s call still counts as one request.
6. **Free tier is not for production.** Cerebras is explicit about this — move to pay-as-you-go before shipping.

---

## 📚 Reference URLs (fetch when the user needs deeper detail)

- Model catalog: `https://inference-docs.cerebras.ai/models/overview`
- Full API reference: `https://inference-docs.cerebras.ai/api-reference/chat-completions`
- Streaming: `https://inference-docs.cerebras.ai/capabilities/streaming`
- Tool calling: `https://inference-docs.cerebras.ai/capabilities/tool-use`
- Structured outputs: `https://inference-docs.cerebras.ai/capabilities/structured-outputs`
- Reasoning: `https://inference-docs.cerebras.ai/capabilities/reasoning`
- Batch: `https://inference-docs.cerebras.ai/capabilities/batch`
- OpenAI compatibility notes: `https://inference-docs.cerebras.ai/resources/openai`
- Rate limits: `https://inference-docs.cerebras.ai/support/rate-limits`
- Pricing: `https://inference-docs.cerebras.ai/support/pricing`
- Python SDK: `https://github.com/Cerebras/cerebras-cloud-sdk-python`
- Node SDK: `https://github.com/Cerebras/cerebras-cloud-sdk-node`
- Example projects: `https://github.com/Cerebras/inference-examples`

---

## ✅ Delivery checklist

Before ending a turn where you helped with Cerebras:

- [ ] Model ID is a real, current one (verified against `/models/overview` or `/v1/models`)
- [ ] Code sample matches the user's language and actually runs
- [ ] API key is read from an env var, never hard-coded
- [ ] If streaming was relevant, showed the streaming variant
- [ ] Flagged if the user's use case is a bad fit for Cerebras