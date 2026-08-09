#!/usr/bin/env python3
"""Test script to verify authentication and catalog lookup flow."""

import sys
from app.db.session import SessionLocal
from app.models.instruments import InstrumentVersion, Instrument
from app.models.identity import User
from app.core.auth import verify_password, create_access_token
from app.core.config import settings
from app.seed.loader import seed_id
from sqlalchemy import select

def test_users():
    """Test that seeded users exist and passwords work."""
    print("=" * 60)
    print("TEST 1: User Authentication")
    print("=" * 60)
    db = SessionLocal()
    
    test_accounts = [
        ("evaluado", "psico-dev-evaluado"),
        ("psicologo", "psico-dev-psicologo"),
        ("admin", "psico-dev-admin"),
    ]
    
    for username, password in test_accounts:
        user = db.scalar(select(User).where(User.username == username))
        if not user:
            print(f"❌ User '{username}' NOT FOUND")
            continue
            
        password_valid = verify_password(password, user.password_hash)
        status = "✅" if password_valid else "❌"
        print(f"{status} {username}: password_valid={password_valid}, is_active={user.is_active}")
    
    db.close()
    print()

def test_catalog():
    """Test published versions and catalog lookup."""
    print("=" * 60)
    print("TEST 2: Catalog & Published Versions")
    print("=" * 60)
    db = SessionLocal()
    
    # List all published versions
    versions = db.scalars(
        select(InstrumentVersion)
        .join(Instrument)
        .where(InstrumentVersion.status == "published")
    ).all()
    
    print(f"Found {len(versions)} published version(s):")
    for v in versions:
        print(f"  - {v.instrument.key} v{v.version_no}")
        print(f"    ID: {v.id}")
        print(f"    Status: {v.status}, Immutable: {v.is_immutable}")
    
    # Test seed ID resolution
    print("\nSeed ID Resolution:")
    tp_s_01_v1_id = seed_id("TP-S-01:v1")
    print(f"  seed_id('TP-S-01:v1') = {tp_s_01_v1_id}")
    
    version = db.get(InstrumentVersion, tp_s_01_v1_id)
    if version:
        print(f"  ✅ Found in DB: {version.instrument.key} v{version.version_no}")
    else:
        print(f"  ❌ NOT FOUND in DB")
    
    db.close()
    print()

def test_jwt():
    """Test JWT token generation."""
    print("=" * 60)
    print("TEST 3: JWT Token Generation")
    print("=" * 60)
    db = SessionLocal()
    
    user = db.scalar(select(User).where(User.username == "evaluado"))
    if user:
        token = create_access_token(
            user.id, 
            user.username, 
            ["evaluado"],
            settings.jwt_secret
        )
        print(f"✅ Token generated for 'evaluado':")
        print(f"   {token[:50]}...")
    else:
        print("❌ User 'evaluado' not found")
    
    db.close()
    print()

def test_consent():
    """Test consent versions."""
    print("=" * 60)
    print("TEST 4: Consent Versions")
    print("=" * 60)
    db = SessionLocal()
    
    from app.models.consent import ConsentVersion
    consents = db.scalars(select(ConsentVersion)).all()
    
    print(f"Found {len(consents)} consent version(s):")
    for c in consents:
        status = "ACTIVE" if c.is_active else "inactive"
        print(f"  - v{c.version_no} ({status})")
        print(f"    ID: {c.id}")
    
    db.close()
    print()

def main():
    try:
        test_users()
        test_catalog()
        test_jwt()
        test_consent()
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
