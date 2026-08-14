# Signal Engine Specification

## Purpose

The signal engine determines when something is sufficiently unusual or persistent to deserve attention.

The engine is deterministic.

The LLM does not decide whether a 3% move is significant.

## Signal categories

### Price
- DAILY_GAIN
- DAILY_DECLINE
- WEEKLY_GAIN
- WEEKLY_DECLINE
- PERSISTENT_GAIN
- PERSISTENT_DECLINE
- NEW_HIGH
- LARGE_DRAWDOWN
- REFERENCE_LEVEL_CROSS

### Volume
- HIGH_RELATIVE_VOLUME
- PERSISTENT_HIGH_VOLUME
- HIGH_VOLUME_GAIN
- HIGH_VOLUME_DECLINE

### Fundamental
- REVENUE_ACCELERATION
- REVENUE_DECELERATION
- EPS_IMPROVEMENT
- EPS_DETERIORATION
- MARGIN_IMPROVEMENT
- MARGIN_DETERIORATION
- FCF_IMPROVEMENT
- FCF_DETERIORATION
- DEBT_CHANGE
- GUIDANCE_RAISE
- GUIDANCE_CUT

### Expectations / valuation
- EARNINGS_ESTIMATE_UP
- EARNINGS_ESTIMATE_DOWN
- VALUATION_EXPANSION
- VALUATION_COMPRESSION
- FUNDAMENTAL_VALUATION_DIVERGENCE

### Events
- EARNINGS
- MAJOR_FILING
- MANAGEMENT_CHANGE
- REGULATORY_EVENT
- MATERIAL_CORPORATE_EVENT
- MAJOR_NEWS

### Portfolio
- POSITION_WEIGHT_CHANGE
- POSITION_ABOVE_TARGET
- POSITION_BELOW_TARGET
- CONCENTRATION_INCREASE
- SECTOR_EXPOSURE_CHANGE
- MATERIAL_PORTFOLIO_CONTRIBUTION

## Direction

Every applicable signal should have:
- positive
- negative
- mixed
- neutral

## Severity

Initial conceptual levels:
- INFO
- NOTABLE
- MATERIAL
- HIGH

Exact thresholds are configuration, not constants embedded in business logic.

## Daily escalation

A daily movement should normally trigger only a brief report item.

Example:
- daily return exceeds configured threshold

Context:
- sector move
- market move
- relative volume
- obvious events/news

## Weekly escalation

Persistent movement should trigger deeper analysis.

Example conceptual rule:
- several same-direction sessions
- cumulative movement exceeds configured threshold
- optional relative-volume confirmation

The exact values must be decided/tested.

## Fundamental escalation

Fundamental changes can trigger analysis without a major price movement.

Examples:
- repeated revenue deceleration
- earnings estimate deterioration
- guidance change
- material margin movement

## Portfolio escalation

A moderate stock signal becomes more important when:
- position is large
- position weight changed materially
- stock is a major portfolio contributor/detractor
- thesis is central to portfolio strategy

## Opportunity detection

The engine should explicitly look for:
- improving fundamentals
- improving earnings expectations
- reasonable/improving valuation
- price weakness despite stable/improving fundamentals
- persistent appreciation with improving fundamentals
- portfolio underweight plus improving thesis

These are "investigate" signals, not Buy signals.

## Important distinction

Price movement is an observation.

The engine must not infer:
- price down = bad
- price up = good

It should combine price, business, valuation, external environment, and portfolio context.
