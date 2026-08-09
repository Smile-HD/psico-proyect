#!/usr/bin/env python3
"""Debug catalog resolution."""

from app.db.session import SessionLocal
from app.api.routes.catalog import resolve_published_version_id
from app.seed.loader import seed_id
from app.models.instruments import InstrumentVersion

db = SessionLocal()

test_key = "TP-S-01:v1"
print(f"Testing resolution for: {test_key}")
print(f"Seed ID: {seed_id(test_key)}")

# Check if version exists
ver = db.get(InstrumentVersion, seed_id(test_key))
print(f"Version found: {ver is not None}")
if ver:
    print(f"  Status: {ver.status}")
    print(f"  Is published: {ver.status == 'published'}")

# Try resolve
try:
    result = resolve_published_version_id(db, test_key)
    print(f"✅ Resolution succeeded: {result}")
except Exception as e:
    print(f"❌ Resolution failed: {e}")

db.close()
