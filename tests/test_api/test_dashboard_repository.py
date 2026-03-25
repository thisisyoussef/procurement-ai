"""Tests for dashboard repository query behavior."""

import asyncio

from sqlalchemy.dialects import postgresql

from app.repositories.dashboard_repository import list_supplier_contacts_for_user


class _EmptyResult:
    def all(self):
        return []


class _CaptureSession:
    def __init__(self) -> None:
        self.stmt = None

    async def execute(self, stmt):
        self.stmt = stmt
        return _EmptyResult()


def test_list_supplier_contacts_for_user_adds_phone_digits_condition_for_digit_query():
    session = _CaptureSession()

    asyncio.run(
        list_supplier_contacts_for_user(
            session=session,
            user_id="00000000-0000-0000-0000-000000000001",
            contact_query="3125550142",
        )
    )

    compiled = session.stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "regexp_replace" in sql
    assert "\\D" in str(compiled.params)
    assert "3125550142" in str(compiled.params)


def test_list_supplier_contacts_for_user_skips_phone_digits_condition_for_non_digit_query():
    session = _CaptureSession()

    asyncio.run(
        list_supplier_contacts_for_user(
            session=session,
            user_id="00000000-0000-0000-0000-000000000001",
            contact_query="acme",
        )
    )

    compiled = session.stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "regexp_replace" not in sql
