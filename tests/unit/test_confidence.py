import pytest
from app.schemas.agent import AgentState, IntentResult, RetrievedContext
from app.agent.nodes import compute_confidence

def test_compute_confidence_high():
    state = AgentState(
        correlation_id="test", query="test query",
        channel="email", identifier="test@test.com",
        author_id="123",
        intent_result=IntentResult(
            intent="ROYALTY",
            reasoning="test",
            confidence=0.9,
        ),
        retrieved_contexts=[
            RetrievedContext(source_id="kb:chunk_1", content="test",
                             source_type="kb", score=0.88)
        ],
        final_response="This is a test response [kb:chunk_1]",
    )
    score = compute_confidence(state)
    assert score >= 0.80

def test_compute_confidence_low():
    state = AgentState(
        correlation_id="test", query="test query",
        channel="email", identifier="test@test.com",
        author_id=None,
        intent_result=IntentResult(
            intent="UNKNOWN",
            reasoning="test",
            confidence=0.3,
        ),
        retrieved_contexts=[],
        final_response="I am not sure.",
    )
    score = compute_confidence(state)
    assert score < 0.80
