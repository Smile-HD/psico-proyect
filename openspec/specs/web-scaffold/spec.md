# Web Scaffold Specification

## Purpose

Minimal Next.js vertical slice proving the compose network: a single page that calls the API `/health` and shows seed status. UI texts are in Spanish.

## Requirements

### Requirement: Health and Seed Status Page

`apps/web` MUST render a single page that calls the API health endpoint and seed status, showing health OK and the seed counts (20 items, 1 reference set, 30 profiles). All user-facing texts MUST be in Spanish.

#### Scenario: Happy render

- GIVEN the API is healthy and seeded
- WHEN the page loads
- THEN it shows health OK and seed counts 20 items / 1 reference set / 30 profiles in Spanish

#### Scenario: API unavailable

- GIVEN the API is unreachable
- WHEN the page loads
- THEN a friendly Spanish error is shown instead of a crash or stack trace

### Requirement: Vertical Slice over the Compose Network

The page MUST run inside the compose network and reach the API by service name, proving the network wiring for later phases.

#### Scenario: Internal network reachability

- GIVEN `web` and `api` on the same compose network
- WHEN the page fetches the health endpoint by service name
- THEN the request succeeds without host port mapping or CORS workarounds

#### Scenario: Seed status reflects the database

- GIVEN a freshly seeded database
- WHEN the page requests seed status
- THEN counts match the live database, not a hardcoded value
