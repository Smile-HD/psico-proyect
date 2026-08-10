# Delta for Catalog API

## ADDED Requirements

### Requirement: Published Version Listing

The catalog MUST expose a published-version listing endpoint (`GET /api/v1/catalog/published-versions`) that returns published version summaries (instrument key, version id, labels) to `admin`, `psicólogo`, and `evaluado`. Draft and archived versions MUST never appear in the listing, even as disabled choices. The listing MUST be labels-only: no numeric option values, answer keys, or scoring data.

#### Scenario: Evaluado discovers published versions

- GIVEN a published synthetic version and a draft version
- WHEN an `evaluado` requests the listing
- THEN only the published version summary is returned

#### Scenario: Draft and archived never listed

- GIVEN draft and archived version ids
- WHEN the listing is requested by any role
- THEN neither id appears in the response

#### Scenario: Labels only

- GIVEN the listing response
- WHEN its fields are enumerated
- THEN it contains labels and identifiers only
- AND no numeric option values or scoring data are present
