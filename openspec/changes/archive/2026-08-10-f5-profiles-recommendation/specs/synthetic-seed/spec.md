# Delta for Synthetic Seed

## ADDED Requirements

### Requirement: Recommendation Seed Content

Seed MUST create 4–6 invented synthetic programs under `faculty:dev` (institution `institution:dev`), each with a distinct `code` and a stable key in the `program:<slug>` namespace, plus active `recommendation_rules` rows (keys `rule:<program-key>:<n>`, `is_active=true`) referencing the exact scale labels `Intereses`, `Aptitud verbal`, `Aptitud numérica`, `Razonamiento abstracto`, `Valores/preferencias`, and/or `overall`. Every seeded row MUST set `synthetic=true` / `source='seed'`. `recommendation_results` MUST NEVER be seeded (runtime-only). The seed MUST remain idempotent, MUST include the recommendation tables in manifest counts and `--reset` scope, and MUST bump `SEED_VERSION`. `--reset` MUST remove only seed-owned recommendation rows; runtime results referencing seed rules trigger the existing atomic preflight `CONFLICT` with no deletion.

#### Scenario: Programs and rules seeded

- GIVEN a completed seed
- WHEN counting `programs` under `faculty:dev` and `recommendation_rules` rows
- THEN 4–6 invented programs exist alongside `program:dev`
- AND every program has at least one active rule whose `scale` matches a seeded scale label or `overall`

#### Scenario: Results are never seeded

- GIVEN a completed seed
- WHEN counting `recommendation_results`
- THEN the count is 0
- AND all seeded recommendation rows are flagged synthetic with `source='seed'`

#### Scenario: Reseed is idempotent

- GIVEN a seeded database
- WHEN seed runs a second time
- THEN program and rule ids and counts are unchanged
- AND a new `seed_manifest` run row is appended
