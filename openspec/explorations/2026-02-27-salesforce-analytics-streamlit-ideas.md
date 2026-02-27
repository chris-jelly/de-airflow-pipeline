# Salesforce Analytics + Streamlit Exploration

Date: 2026-02-27
Mode: Explore (no implementation)

## Context

We explored what analytics can be built on top of existing dbt marts in `dags/dbt/` with a small Streamlit app.

Current marts/models in play:
- `dim_salesforce_accounts`
- `fct_salesforce_opportunities`
- `opportunity_history_snapshot`

## Exploration Goal

Design a simple, useful example analytics app that uses current marts without adding new dbt models.

## Candidate App Concept

"Sales Pipeline Pulse" with 3 lightweight tabs:
1. Pipeline Overview
2. Forecast and Conversion
3. History and Change

## Suggested MVP Metrics (Available Today)

From `fct_salesforce_opportunities`:
- Open pipeline amount
- Weighted pipeline amount (`amount * probability`)
- Opportunity count
- Win rate (`closed won / closed`)
- Average deal size
- Stage distribution
- Close-date buckets (next 30/60/90 days)

From `dim_salesforce_accounts`:
- Pipeline by industry
- Pipeline by account type
- Top accounts by open pipeline
- Geographic cuts using billing fields

From `opportunity_history_snapshot`:
- Day-over-day pipeline trend
- Day-over-day weighted pipeline trend
- Stage mix trend over time
- Largest daily changes in pipeline

## Proposed Streamlit Information Architecture

Sidebar filters:
- Date range
- Industry
- Account type
- Stage multi-select
- Active account toggle

Tab 1 - Overview:
- KPI cards
- Stage bar chart
- Open opportunities table

Tab 2 - Forecast:
- Weighted pipeline by close month
- Win rate by stage
- "Likely to close" list (high probability + near close date)

Tab 3 - History:
- Pipeline and weighted pipeline trend
- Stage mix trend
- Biggest day-over-day movers

## Why This Fits Current Modeling

- `fct_salesforce_opportunities` is already analytics-friendly (opportunity + account context)
- `opportunity_history_snapshot` provides daily historical tracking
- Existing dbt tests already guard core quality dimensions:
  - non-negative opportunity amount
  - allowed stage set monitoring
  - snapshot grain uniqueness

## Known Constraints and Caveats

- Contacts are modeled in intermediate, but not yet exposed in marts for contact analytics
- Snapshot is daily, so intraday changes are not visible
- Forecast reliability depends on Salesforce probability hygiene

## Useful Follow-On Questions

- Which KPI definitions should be canonical and documented first?
- Should weighted pipeline be probability-only or stage-adjusted?
- Should we include owner-level views in MVP?
- Is this internal-only or stakeholder-facing?

## If Promoted to a Change

Potential next step is creating an OpenSpec change for:
- metric definitions
- app scope and non-goals
- minimal data access pattern
- acceptance criteria for a v1 dashboard
