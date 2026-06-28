import pytest
from uuid import uuid4
from core.graph import agent_app
from core.data_contracts import AlertPayload, SystemMetrics

@pytest.fixture
def mock_critical_alert() -> AlertPayload:
    """Fixture providing a mock critical alert payload."""
    metrics = SystemMetrics(cpu_usage_percent=95.0, memory_usage_percent=85.0)
    return AlertPayload(
        alert_id=f"alert-{uuid4().hex[:8]}",
        severity="CRITICAL",
        description="Resource exhaustion detected! High CPU and memory.",
        raw_metrics=metrics
    )

def test_graph_interrupts_at_safety_boundary(mock_critical_alert):
    """
    Tests if the LangGraph execution properly halts at the 'executor' node
    to enforce Human-in-the-Loop (HITL) authorization.
    """
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_input = {"alert": mock_critical_alert}

    # Execute graph until breakpoint
    for _ in agent_app.stream(initial_input, config):
        pass
    
    # Retrieve the state snapshot
    snapshot = agent_app.get_state(config)
    
    # Assertions
    assert snapshot.next is not None, "Graph finished execution prematurely."
    assert snapshot.next[0] == "executor", "Graph did not interrupt at the 'executor' node."
    
    state_values = snapshot.values
    assert state_values.get("proposed_remediation") is not None
    assert "KILL PID 2044" in state_values["proposed_remediation"]

def test_graph_escalation_fallback():
    """
    Tests if an unrecognized alert correctly routes to the escalation node
    without triggering infrastructure mutations.
    """
    metrics = SystemMetrics(cpu_usage_percent=10.0, memory_usage_percent=10.0)
    unknown_alert = AlertPayload(
        alert_id="alert-unknown",
        severity="WARNING",
        description="Unknown anomaly detected in network I/O.",
        raw_metrics=metrics
    )
    
    config = {"configurable": {"thread_id": str(uuid4())}}
    
    # Execute graph
    for _ in agent_app.stream({"alert": unknown_alert}, config):
        pass
        
    snapshot = agent_app.get_state(config)
    
    # Should complete execution (hit END)
    assert len(snapshot.next) == 0
    assert snapshot.values.get("resolution_status") == "Escalated"
