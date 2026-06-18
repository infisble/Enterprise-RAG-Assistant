from app.schemas.chat import Citation
from app.services.rag import RagService


def test_grounding_requires_overlap(db_session) -> None:
    service = RagService(db_session)
    citations = [
        Citation(
            document_id=1,
            document_title="HR Policy",
            chunk_id=1,
            chunk_index=0,
            score=1.0,
            text="Vacation requests should be submitted two weeks before absence.",
        )
    ]

    assert service._has_grounding("When should vacation requests be submitted?", citations)
    assert not service._has_grounding("What is the cafeteria menu?", citations)


def test_real_provider_answer_requires_context(db_session, monkeypatch) -> None:
    service = RagService(db_session)
    monkeypatch.setattr("app.services.rag.settings.llm_provider", "openai")

    assert not service._answer_is_grounded("Employees get approval from managers.", [])
