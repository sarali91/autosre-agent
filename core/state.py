import operator
from typing import TypedDict, Annotated, List, Optional
from core.data_contracts import AlertPayload

class AgentState(TypedDict):
    """
    Centralized state dictionary for the LangGraph state machine.
    Maintains the context of the incident throughout the multi-turn ReAct loop.
    """
    alert: AlertPayload
    
    # Using Annotated with operator.add ensures logs are appended, not overwritten
    diagnostic_logs: Annotated[List[str], operator.add]
    
    # Routing signals
    next_action: Optional[str]
    proposed_remediation: Optional[str]
    resolution_status: Optional[str]
