# Delta for Synthetic Seed

## ADDED Requirements

### Requirement: Reference Set Value Shape

Reference set `RS-TP-S-01` MUST contain exactly 30 `reference_values` rows, all synthetic/research-only: 10 per-scale rows (one `mean` and one `sd` per scale, keyed by the scale label matching `items.json` labels exactly) and 20 `overall` rows mapping raw 1–20 to percentile/T/eneatype. The `norm_note` MUST be the pinned research-only disclaimer verbatim. F4 consumes this shape read-only; the seed MUST NOT change.

#### Scenario: Seeded reference rows match the contract

- GIVEN a completed seed
- WHEN counting `reference_values` for `RS-TP-S-01`
- THEN 30 rows exist: 10 per-scale mean/sd plus 20 overall rows

#### Scenario: Scale labels are the join key

- GIVEN the seeded per-scale rows
- WHEN comparing their `scale` values with `items.json` labels
- THEN they match exactly
