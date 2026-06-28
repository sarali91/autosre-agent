import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import AgentState
from core.tools.db_analyzer import DBAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. Node Definitions (Isolated business logic)
# ==========================================

def state_initializer(state: AgentState) -> Dict[str, Any]:
    """Ingests the alert and initializes the tracing context."""
    logger.info(f"Ingesting alert ID: {state['alert'].alert_id}")
    return {"diagnostic_logs": ["System initialized. Alert ingested."]}

def llm_reasoning_engine(state: AgentState) -> Dict[str, Any]:
    """
    Simulates the ReAct LLM component.
    Evaluates current diagnostic logs and decides the next traversal edge.
    """
    logger.info("Evaluating system context and logs...")
    
    logs_str = str(state.get("diagnostic_logs", []))
    alert_desc = state['alert'].description
    
    if "Resource exhaustion" in alert_desc and "blocking transaction" not in logs_str:
        logger.info("Decision: Insufficient context. Routing to DB diagnostics.")
        return {"next_action": "use_db_tool"}
    elif "blocking transaction" in logs_str:
        logger.info("Decision: Root cause identified. Drafting remediation plan.")
        return {"next_action": "draft_remediation"}
    else:
        logger.warning("Decision: Fallback triggered. Escalating to human SRE.")
        return {"next_action": "escalate"}

def db_tool_executor(state: AgentState) -> Dict[str, Any]:
    """Executes the database diagnostic tool."""
    result = DBAnalyzer.check_active_locks()
    return {"diagnostic_logs": [f"DB Analysis: {result}"]}

def remediation_planner(state: AgentState) -> Dict[str, Any]:
    """Drafts the infrastructure mutation payload."""
    plan = "KILL PID 2044; CREATE INDEX idx_payment_status ON orders;"
    logger.info(f"Remediation drafted: {plan}")
    return {"proposed_remediation": plan}

def execute_mutation(state: AgentState) -> Dict[str, Any]:
    """Executes the state-mutating infrastructure command."""
    # This node is protected by the HITL interrupt.
    mutation = state.get("proposed_remediation")
    logger.warning(f"EXECUTING MUTATION: {mutation}")
    return {"resolution_status": "Resolved", "diagnostic_logs": ["Mutation executed successfully."]}

def escalate_to_human(state: AgentState) -> Dict[str, Any]:
    """Terminal node for unresolvable incidents."""
    logger.error("Paging SRE team via PagerDuty...")
    return {"resolution_status": "Escalated"}

# ==========================================
# 2. Graph Compilation & Edge Routing
# ==========================================

def route_after_reasoning(state: AgentState) -> str:
    """Conditional routing logic based on LLM output."""
    action = state.get("next_action")
    mapping = {
        "use_db_tool": "db_tool",
        "draft_remediation": "planner",
    }
    return mapping.get(action, "escalation")

def build_graph() -> StateGraph:
    """Constructs and compiles the DAG."""
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("initializer", state_initializer)
    workflow.add_node("reasoning", llm_reasoning_engine)
    workflow.add_node("db_tool", db_tool_executor)
    workflow.add_node("planner", remediation_planner)
    workflow.add_node("executor", execute_mutation)
    workflow.add_node("escalation", escalate_to_human)

    # Define strict edges
    workflow.set_entry_point("initializer")
    workflow.add_edge("initializer", "reasoning")
    
    workflow.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {"db_tool": "db_tool", "planner": "planner", "escalation": "escalation"}
    )
    
    workflow.add_edge("db_tool", "reasoning")  # Loop back to reasoning
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", END)
    workflow.add_edge("escalation", END)

    return workflow

# Compile with Memory Checkpointer and Human-in-the-Loop breakpoint
memory_saver = MemorySaver()
agent_app = build_graph().compile(checkpointer=memory_saver, interrupt_before=["executor"])
