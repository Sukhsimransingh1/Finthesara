
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.services.research_repository import ResearchRepository


def test_first_row_returns_mapping() -> None:
    row = {"id": str(uuid4())}

    assert (
        ResearchRepository._first_row(
            SimpleNamespace(data=[row]),
            "missing",
        )
        == row
    )


@pytest.mark.parametrize(
    "data",
    [None, [], ["not-a-row"]],
)
def test_first_row_rejects_invalid_response(
    data: object,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="Research row missing",
    ):
        ResearchRepository._first_row(
            SimpleNamespace(data=data),
            "Research row missing",
        )


def test_project_owner_check_rejects_non_owner() -> None:
    class Query:
        def select(self, *_: object) -> Query:
            return self

        def eq(self, *_: object) -> Query:
            return self

        def limit(self, *_: object) -> Query:
            return self

        def execute(self) -> SimpleNamespace:
            return SimpleNamespace(data=[])

    class Client:
        def table(self, _: str) -> Query:
            return Query()

    repository = ResearchRepository(
        client=Client(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        PermissionError,
        match="access denied",
    ):
        repository.assert_project_owner(
            uuid4(),
            uuid4(),
        )
