# LLM Configuration Guide

**Story 6.5 AC4:** Documentation for OpenAI LLM configuration, focusing on gpt-5-nano requirements.

## Overview

This document describes the configuration requirements for OpenAI LLM models used in FisioRAG, with specific guidance for the gpt-5-nano model which has unique temperature constraints.

## Supported Models

### gpt-5-nano

**Primary model for chat generation and classification.**

- **Model ID:** `gpt-5-nano` or `gpt-5-nano-2025-08-07`
- **Use Case:** Fast, deterministic responses with lower cost
- **Temperature Requirement:** **MUST use default temperature (1.0)**
- **Configuration:** Do NOT set `OPENAI_TEMPERATURE_CHAT` when using gpt-5-nano

**Why gpt-5-nano requires default temperature:**

OpenAI's gpt-5-nano model is optimized for specific use cases and has architectural constraints that require using the default temperature value of 1.0. Explicitly setting temperature=0 or any other value causes API errors with the message: "Invalid temperature parameter for gpt-5-nano model."

The system automatically handles this constraint by detecting "nano" in the model name and skipping temperature override.

### gpt-4

**Alternative model for complex reasoning.**

- **Model ID:** `gpt-4`, `gpt-4-turbo`, `gpt-4-turbo-preview`
- **Use Case:** Complex reasoning, detailed analysis
- **Temperature:** Configurable (0.0 - 2.0)
- **Configuration:** Set `OPENAI_TEMPERATURE_CHAT` to desired value (e.g., 0.7)

### gpt-3.5-turbo

**Alternative model for cost optimization.**

- **Model ID:** `gpt-3.5-turbo`, `gpt-3.5-turbo-16k`
- **Use Case:** Simple queries, cost-sensitive applications
- **Temperature:** Configurable (0.0 - 2.0)
- **Configuration:** Set `OPENAI_TEMPERATURE_CHAT` to desired value

## Configuration Guide

### Environment Variables

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-...

# Model Selection
OPENAI_MODEL=gpt-5-nano

# Chat Temperature (model-specific)
# For gpt-5-nano: Leave empty or unset
# For gpt-4/gpt-3.5: Set to 0.0-2.0
OPENAI_TEMPERATURE_CHAT=

# Classification Temperature (used for content classification)
OPENAI_TEMPERATURE_CLASSIFICATION=1.0

# Enable LLM configuration refactoring (Story 2.12)
LLM_CONFIG_REFACTOR_ENABLED=true
```

### Configuration Examples

#### Example 1: gpt-5-nano (Recommended)

```bash
OPENAI_MODEL=gpt-5-nano
OPENAI_TEMPERATURE_CHAT=
# Temperature automatically defaults to 1.0 for nano models
```

#### Example 2: gpt-4 with Custom Temperature

```bash
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE_CHAT=0.7
# Temperature 0.7 provides balanced creativity and consistency
```

#### Example 3: gpt-3.5-turbo for Deterministic Responses

```bash
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE_CHAT=0.0
# Temperature 0.0 provides deterministic responses
```

## Implementation Details

### Temperature Handling (Story 6.5)

The system automatically handles temperature configuration based on the selected model:

**Location:** `apps/api/api/services/chat_service.py`

```python
def _get_chat_llm(resolved_settings: Settings) -> ChatOpenAI:
    model = resolved_settings.openai_model
    model_kwargs = {"model": model}
    
    # gpt-5-nano requires default temperature (1.0) - do not override
    if "nano" in model.lower():
        logger.info({
            "event": "chat_llm_nano_default_temperature",
            "model": model,
            "temperature_decision": "default_1.0_for_nano",
            "temperature_override_skipped": True,
            "reason": "gpt-5-nano requires default temperature (1.0)"
        })
    elif resolved_settings.openai_temperature_chat is not None:
        model_kwargs["temperature"] = resolved_settings.openai_temperature_chat
    
    return ChatOpenAI(**model_kwargs)
```

**Key Points:**
- System detects "nano" in model name
- Temperature override is automatically skipped for nano models
- Structured logging provides transparency for temperature decisions
- Non-nano models can use custom temperature via `OPENAI_TEMPERATURE_CHAT`

### Other LLM Initialization Points

**Admin Debug Endpoint:** `apps/api/api/routers/admin.py`

```python
# Story 6.5 AC1: Handle gpt-5-nano temperature constraint
model_kwargs = {"model": settings.openai_model}
if "nano" not in settings.openai_model.lower():
    model_kwargs["temperature"] = 0
llm = ChatOpenAI(**model_kwargs)
```

**Classifier:** `apps/api/api/knowledge_base/classifier.py`

```python
# Correctly configured for gpt-5-nano
return ChatOpenAI(model="gpt-5-nano", temperature=1, **client_args)
```

## Temperature Parameter Guide

### What is Temperature?

Temperature controls randomness in the LLM's output:
- **0.0:** Deterministic, consistent responses (picks most likely tokens)
- **0.5-0.7:** Balanced creativity and consistency (recommended for most use cases)
- **1.0:** Default OpenAI temperature, good balance
- **1.5-2.0:** High creativity, more random responses

### When to Use Different Temperatures

| Temperature | Use Case | Examples |
|------------|----------|----------|
| 0.0 | Factual Q&A, classification, structured output | Medical information retrieval, diagnosis classification |
| 0.7 | General chat, explanations | Patient education, treatment explanations |
| 1.0 | Default, balanced responses | General-purpose chat, gpt-5-nano |
| 1.5+ | Creative writing, brainstorming | Not typically used in medical applications |

### gpt-5-nano Exception

**Important:** gpt-5-nano does NOT support custom temperature values. The model architecture requires using the default temperature of 1.0. This is enforced by OpenAI's API and cannot be overridden.

## Testing Configuration

### Unit Tests

Test temperature handling for different models:

```python
# Test gpt-5-nano skips temperature override
settings_nano = Settings(
    openai_model="gpt-5-nano",
    openai_temperature_chat=0.5,  # Should be ignored
)
llm_nano = _get_chat_llm(settings_nano)
# Verify temperature was NOT overridden

# Test gpt-4 applies temperature
settings_gpt4 = Settings(
    openai_model="gpt-4",
    openai_temperature_chat=0.7,
)
llm_gpt4 = _get_chat_llm(settings_gpt4)
# Verify temperature=0.7 was applied
```

### E2E Tests

Story 6.5 includes comprehensive E2E test (`test_rag_e2e_complete.py`) that validates:
- Document ingestion → embeddings
- Semantic search retrieval
- Generation with gpt-5-nano
- Temperature handling verification
- Structured logging and metrics

**Run E2E tests:**
```bash
# E2E tests require real OpenAI API
RUN_E2E_REAL=1 poetry run pytest tests/test_rag_e2e_complete.py -v
```

## Troubleshooting

### Error: "Invalid temperature parameter for gpt-5-nano"

**Cause:** Explicitly setting temperature for gpt-5-nano model

**Solution:** 
1. Ensure `OPENAI_TEMPERATURE_CHAT` is empty or unset in `.env`
2. Verify code is using updated `_get_chat_llm()` from Story 6.5
3. Check logs for "temperature_override_skipped" event

### Generation Failures with gpt-5-nano

**Symptoms:** API errors, empty responses, timeout errors

**Debug Steps:**
1. Verify `OPENAI_API_KEY` is valid
2. Check OpenAI API status: https://status.openai.com
3. Review structured logs in `reports/e2e/6.5-rag-run-*.log`
4. Check token usage and rate limits

### Performance Issues

**Symptoms:** Slow response times, high latency

**Solutions:**
- Monitor latency metrics in `reports/e2e/6.5-generation-perf-*.json`
- Check P95/P99 latency percentiles
- Consider using gpt-5-nano-2025-08-07 (latest version)
- Review chunk count provided to LLM (reduce if too many)

## Monitoring & Observability

### Structured Logging (Story 6.5 AC5)

All LLM generation events emit structured logs:

```json
{
  "event": "llm_generation_completed",
  "timestamp": "2025-01-20T14:23:45.123Z",
  "session_id": "uuid",
  "model": "gpt-5-nano",
  "temperature_decision": "default_1.0_for_nano",
  "temperature_override_skipped": true,
  "latency_ms": 1234,
  "tokens_prompt": 450,
  "tokens_completion": 120,
  "tokens_total": 570,
  "cost_usd": 0.00285,
  "chunks_provided": 5,
  "chunks_cited": 3
}
```

### Metrics Files

- **Token Metrics:** `reports/e2e/6.5-token-metrics-YYYYMMDD.json`
- **Performance Metrics:** `reports/e2e/6.5-generation-perf-YYYYMMDD.json`
- **Execution Logs:** `reports/e2e/6.5-rag-run-YYYYMMDD.log`

## References

- [OpenAI Models Documentation](https://platform.openai.com/docs/models)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)
- [Story 6.5: LLM Generation Fix & E2E Validation](../../stories/6.5.llm-generation-fix-e2e-validation.md)
- [Story 2.12: LLM Configuration Refactoring](../../stories/2.12.llm-configuration-refactoring.md)

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-20 | 1.0 | Initial documentation - gpt-5-nano temperature requirements | Dev Agent (Story 6.5) |

