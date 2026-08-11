# Scoring Engine Specification

## Purpose

The F4 pure scoring chain: responses + pinned instrument version + reference set → raw → direct → transformed scores. The engine is a pure function (no DB, no I/O, no side effects) over the private, never-public `fixture_projection` 1–5 mapping. Only reference set `RS-TP-S-01` (synthetic, research-only) is consumed in this slice; outputs remain research-only.

## Requirements

### Requirement: Pure Function Contract

The scoring engine MUST be a pure function: identical inputs MUST produce identical outputs, and it MUST NOT access a database, filesystem, network, clock, or random source, and MUST NOT mutate its inputs. Inputs MUST be: response values (1–5 per item, mapped via `fixture_projection`), the pinned `instrument_version_id`, and the reference set id. Outputs MUST be: per-scale raw → direct → transformed (percentile, T, eneatype) plus overall raw → transformed.

#### Scenario: Deterministic pure computation

- GIVEN the same responses, version id, and reference set
- WHEN the engine is invoked twice
- THEN outputs are byte-identical
- AND no DB, network, clock, or filesystem call is made

#### Scenario: Inputs never mutated

- GIVEN response collections passed to the engine
- WHEN the engine returns
- THEN the caller's collections are unchanged

### Requirement: Per-scale Computation

For each scale, raw MUST equal the sum of its 4 mapped 1–5 values (range 4–20). Direct z MUST be `(raw − mean) / sd` using the per-scale `mean`/`sd` reference rows; the join key MUST be the scale LABEL string, matching `items.json` labels exactly. `sd = 0` MUST yield `z = 0`. Percentile MUST be `clamp(round-half-up(100·Φ(z)), 1, 99)`, where Φ is the standard normal CDF evaluated in IEEE-754 double precision (scipy-free, e.g. `math.erf`), agreeing with reference vectors within 1e-12. T MUST be `round-half-up(50 + 10z)`. Eneatype MUST be `clamp(ceil(7·percentile/100), 1, 7)`. Missing, invalid, or non-finite inputs MUST raise a typed integrity error, never fabricate values.

#### Scenario: Happy path scale

- GIVEN a scale with reference mean 12 and sd 2 and a raw of 14
- WHEN the engine computes the scale
- THEN z is 1.0, percentile is 84, T is 60, and eneatype is 6

#### Scenario: Zero variance

- GIVEN a scale reference with sd 0
- WHEN the engine computes z
- THEN z is 0, percentile is 50, T is 50, and eneatype is 4

#### Scenario: Bounds clamped

- GIVEN any valid raw value
- WHEN percentile and eneatype are computed
- THEN percentile is in [1, 99] and eneatype in [1, 7]

#### Scenario: Unknown scale label

- GIVEN a scale label absent from the reference rows
- WHEN the engine computes the scale
- THEN a typed integrity error is raised
- AND no score is produced for that scale

### Requirement: Overall Computation

Overall raw MUST be `round-half-up(1 + 19·(Σraw − 4n)/(16n))`, where n is the number of scales (5 for TP-S-01; Σraw range 20–100 → overall raw 1–20). Overall transformed scores MUST be looked up EXACTLY in the `overall` reference rows (raw 1–20 → percentile/T/eneatype); a missing row MUST raise a typed integrity error, never interpolate or extrapolate.

#### Scenario: Overall happy path

- GIVEN n = 5 and Σraw = 60
- WHEN the overall raw is computed
- THEN overall raw is 11
- AND percentile/T/eneatype come from the overall raw-11 row

#### Scenario: Overall bounds

- GIVEN Σraw = 20 or Σraw = 100
- WHEN the overall raw is computed
- THEN it is exactly 1 or 20 respectively

### Requirement: Reference Input Contract

Each run MUST consume exactly one reference set; this slice MUST support only `RS-TP-S-01`. The engine MUST join per-scale statistics by scale label (exact string match) and overall transformed scores by the computed overall raw integer. Reference rows MUST NOT be modified by the engine.

#### Scenario: Single reference set

- GIVEN reference set `RS-TP-S-01`
- WHEN a run is computed
- THEN only that set's rows are consumed
