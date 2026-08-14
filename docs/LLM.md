# LLM Specification

## Role

The LLM is a research/interpretation layer between structured evidence and the investor.

It should:
- explain
- synthesize
- contextualize
- identify plausible causes
- assess thesis relevance
- summarize uncertainty

It is not the source of truth for financial calculations.

## Input

LLM requests should contain structured, deterministic context such as:
- price changes
- volume and relative volume
- historical comparisons
- fundamentals
- earnings changes
- valuation metrics
- relevant events/news
- sector/market movements
- portfolio weight
- investment thesis
- previous assessments

## Output

Prefer structured output validated against a schema.

Conceptual structure:

```json
{
  "summary": "brief explanation",
  "primary_driver": "company|sector|market|mixed|unknown",
  "direction": "positive|negative|mixed|neutral",
  "facts": [],
  "interpretation": [],
  "uncertainties": [],
  "thesis_impact": "strengthening|stable|monitor|potential_deterioration",
  "portfolio_relevance": "low|medium|high",
  "items_to_watch": []
}
```

## Evidence discipline

The LLM must:
- use supplied facts
- identify uncertainty when evidence is incomplete
- avoid inventing catalysts
- avoid presenting speculation as fact
- distinguish company-specific from broad market movements where evidence permits
- avoid unsupported causal claims

## Decision-support language

Preferred:
- "appears consistent with..."
- "the available evidence suggests..."
- "worth investigating..."
- "the investment thesis may be affected because..."
- "no material deterioration detected..."

Avoid:
- "you should buy"
- "you should sell"
- "guaranteed"
- "will rise"
- "will fall"

## Prompt versioning

Every persisted assessment must record:
- model
- provider
- prompt version
- input hash
- timestamp

This allows analysis of changes in model/prompt behaviour.

## Cost/efficiency

Do not invoke an LLM for every holding every day.

Only escalate when deterministic signals or scheduled report requirements justify analysis.

Stable holdings with no meaningful change should generally be handled without an LLM call.
