"""Unit tests for scoped catalog idempotency behavior."""

from __future__ import annotations

import uuid

import pytest

from app.core.errors import ApiError, CONFLICT
from app.modules.assessment_authoring.idempotency import (
    IdempotencyReplay,
    canonical_request_hash,
    lookup_idempotency,
    store_idempotency,
)
from app.models.idempotency import IdempotencyRecord


class FakeSession:
    def __init__(self) -> None:
        self.rows: dict[tuple[uuid.UUID, str, str, str], IdempotencyRecord] = {}
        self.added: list[IdempotencyRecord] = []

    def scalar(self, _statement):
        return getattr(self, "lookup_row", None)

    def add(self, row: IdempotencyRecord) -> None:
        self.added.append(row)
        self.rows[
            (row.actor_user_id, row.operation, row.resource_scope, row.idempotency_key)
        ] = row

    def flush(self) -> None:
        return None


def test_canonical_hash_is_order_independent_and_changes_with_body() -> None:
    left = {"title": "Synthetic", "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "title": "Synthetic"}
    assert canonical_request_hash(left) == canonical_request_hash(right)
    assert canonical_request_hash({"title": "Different"}) != canonical_request_hash(
        left
    )


def test_miss_stores_a_successful_result_and_same_hash_replays() -> None:
    db = FakeSession()
    actor = uuid.uuid4()
    result = store_idempotency(
        db,
        actor_user_id=actor,
        operation="catalog.create_instrument",
        resource_scope="instrument-key:CAT-01",
        idempotency_key="key-1",
        request_body={"key": "CAT-01"},
        response_status=201,
        response_body={"status": "draft"},
    )
    assert result is db.added[0]
    db.lookup_row = result
    replay = lookup_idempotency(
        db,
        actor_user_id=actor,
        operation="catalog.create_instrument",
        resource_scope="instrument-key:CAT-01",
        idempotency_key="key-1",
        request_body={"key": "CAT-01"},
    )
    assert isinstance(replay, IdempotencyReplay)
    assert replay.status_code == 201
    assert replay.body == {"status": "draft"}


def test_same_key_with_different_body_is_a_conflict_without_a_new_record() -> None:
    db = FakeSession()
    actor = uuid.uuid4()
    stored = store_idempotency(
        db,
        actor_user_id=actor,
        operation="catalog.publish",
        resource_scope="version:one",
        idempotency_key="key-1",
        request_body={"confirm": True},
        response_status=200,
        response_body={"status": "published"},
    )
    db.lookup_row = stored
    with pytest.raises(ApiError) as error:
        lookup_idempotency(
            db,
            actor_user_id=actor,
            operation="catalog.publish",
            resource_scope="version:one",
            idempotency_key="key-1",
            request_body={"confirm": False},
        )
    assert error.value.code == CONFLICT
    assert error.value.message == "idempotency_key_reused"
    assert len(db.added) == 1


def test_distinct_scopes_and_keys_do_not_replay_each_other() -> None:
    db = FakeSession()
    actor = uuid.uuid4()
    first = store_idempotency(
        db,
        actor_user_id=actor,
        operation="catalog.create_instrument",
        resource_scope="instrument-key:CAT-01",
        idempotency_key="key-1",
        request_body={"key": "CAT-01"},
        response_status=201,
        response_body={"key": "CAT-01"},
    )
    db.lookup_row = None
    assert (
        lookup_idempotency(
            db,
            actor_user_id=actor,
            operation="catalog.create_instrument",
            resource_scope="instrument-key:CAT-02",
            idempotency_key="key-1",
            request_body={"key": "CAT-02"},
        )
        is None
    )
    assert first.request_hash != canonical_request_hash({"key": "CAT-02"})
