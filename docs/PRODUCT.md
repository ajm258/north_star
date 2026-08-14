# Product Specification

## 1. Product goal

Provide regular, concise and evidence-based intelligence about an investment portfolio so the investor does not lose touch with holdings, changing fundamentals, market environment, portfolio risks, or opportunities.

The system's primary job is to reduce information blind spots and prevent the investor from being blindsided by meaningful changes.

## 2. Intended investor profile

- Long-term investing.
- Holdings may be very long, long, or medium term.
- No swing trading or intraday trading based on the system.
- Decisions can be made as early as the following day, but the analytical horizon is substantially longer.
- Human remains the final decision maker.

## 3. What the system should answer

- What changed?
- Why did it change?
- Is the change company-specific, sector-wide, or market-wide?
- Is the change persistent?
- Is the business improving or deteriorating?
- Is the original investment thesis strengthening, stable, or weakening?
- Does the change matter to this portfolio?
- Are there positive developments worth investigating?
- Are there negative developments worth investigating?
- What reference levels/context are useful for the investor?

## 4. What it must not do

- Automated trading.
- Automated Buy/Sell execution.
- Binary Buy/Sell recommendations as the primary output.
- Real-time trading signals.
- Short-term price prediction as a core objective.
- Treat every price movement as material.
- Treat price appreciation as automatically positive.
- Treat price declines as automatically negative.

## 5. Core decision-support states

These are informational states, not trade instructions:

- Improving
- Stable
- Emerging
- Monitor
- Investigate
- Potential thesis deterioration
- Potential opportunity / accumulation watch

A future implementation may use severity levels, but wording must preserve the distinction between evidence and an investment decision.

## 6. Positive and negative symmetry

The system must actively look for:

### Positive
- improving revenue growth
- improving earnings
- improving margins
- improving free cash flow
- raised guidance
- improving earnings expectations
- positive company catalysts
- persistent appreciation
- reasonable/improving valuation
- price weakness while fundamentals improve
- portfolio underweight combined with improving fundamentals

### Negative
- slowing revenue growth
- declining earnings
- margin compression
- declining free cash flow
- reduced guidance
- falling earnings expectations
- adverse company events
- persistent decline
- excessive valuation
- price strength while fundamentals deteriorate
- excessive portfolio concentration

## 7. Investment thesis

Each holding may have an investment thesis. The system monitors whether the evidence supporting that thesis is strengthening, stable, or weakening.

The thesis is a key analytical anchor and should be treated as a first-class data object.

## 8. "Why should I care?"

Significant findings should explain why they matter to the portfolio or investment thesis.

Facts should not be presented as recommendations.

Preferred structure:
- Facts
- Interpretation
- Portfolio/thesis relevance
- What to watch

## 9. Early-warning philosophy

The ideal signal occurs before a problem or opportunity becomes obvious.

The system should detect trajectories such as:

Normal → emerging change → persistent change → material change

It should avoid alarm fatigue. Most daily reports should be short and mostly uneventful when nothing material changed.
