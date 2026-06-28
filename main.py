import uuid
import logging
import sys
from ingestion.metrics_scraper import MacMetricsScraper
from core.graph import agent_app

# Set up enterprise logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("autosre.main")

# Mute downstream framework verbose logs to preserve clean console output
logging.getLogger("core.graph").setLevel(logging.ERROR)


def simulate_kafka_consumer():
    """
    Enterprise Orchestration Layer acting as an asynchronous Kafka/RabbitMQ Consumer.
    
    Architectural Purpose:
    1. Peak Shaving: Acts as a message buffer to protect the rate-limited LLM 
       Reasoning Engine from being DDoS'd during cascading infrastructure alert storms.
    2. Distributed Tracing: Extracts/Generates unique trace IDs to enforce complete 
       thread isolation across multi-tenant concurrent state machine runs.
    3. Resilient Fallbacks: Intercepts runtime exceptions (e.g., LLM context timeouts, 
       parsing failures) and gracefully degrades the execution flow to deterministic static runbooks.
    """
    print("\n" + "="*70)
    print("🎧 [KAFKA CONSUMER ACTIVE] Listening to topic: 'infra.telemetry.alerts'")
    print("="*70)
    
    # ------------------------------------------------------------------------
    # STEP 1: Upstream Ingestion Layer (Stateless Scraping)
    # ------------------------------------------------------------------------
    # Setting lower thresholds so it easily triggers an actionable alert for demonstration
    scraper = MacMetricsScraper(cpu_threshold=15.0, mem_threshold=70.0)
    alert_payload = scraper.generate_alert()
    
    if not alert_payload.is_actionable:
        logger.info("Kafka offset committed. Inbound system metrics are healthy. Event dropped.")
        print("✅ [STATUS] System healthy. No agent orchestration required.")
        return
        
    print(f"\n📥 [EVENT CONSUMED] Actionable Event Ingested: {alert_payload.alert_id}")
    print(f"   Context: {alert_payload.description}")
    print("-" * 70)

    # ------------------------------------------------------------------------
    # STEP 2: Distributed Tracing & LangGraph State Isolation
    # ------------------------------------------------------------------------
    # Generating a deterministic trace ID mimicking OpenTelemetry context propagation.
    # This trace ID maps directly to LangGraph's thread_id to guarantee absolute state isolation.
    trace_id = f"trace-id-{alert_payload.alert_id}-{uuid.uuid4().hex[:4]}"
    graph_config = {"configurable": {"thread_id": trace_id}}
    initial_state = {"alert": alert_payload}

    print(f"🔗 [DISTRIBUTED TRACING] Context injected. Trace/Thread ID: {trace_id}")
    print("🧠 [AGENT POOL] Initializing StateGraph orchestration loop...\n")
    
    # ------------------------------------------------------------------------
    # STEP 3: Stream Graph Execution with Resilient Fallback Guardrails
    # ------------------------------------------------------------------------
    try:
        # Simulating execution inside thecompiled StateGraph wrapper
        for event in agent_app.stream(initial_state, graph_config):
            for node_name, _ in event.items():
                print(f"   [Execution Control] Node '{node_name}' traversed successfully.")
                
    except Exception as exc:
        # Enterprise Fallback Mitigation Layer
        # Catching non-deterministic LLM exceptions (e.g., API timeout, Rate Limits, Json Parsing error)
        print("\n" + "⚠️ "*20)
        print(f"🚨 [FALLBACK ACTIVATED] Graceful degradation triggered due to exception: {exc}")
        print("⚠️ "*20)
        print("   -> Bypassing non-deterministic LLM paths.")
        print("   -> Executing static emergency runbook fallback: Routing to human SRE instantly.")
        # In a full production env, you would trigger a fallback state update to the graph here
        return

    # ------------------------------------------------------------------------
    # STEP 4: Human-in-the-Loop (HITL) Authorization Gate
    # ------------------------------------------------------------------------
    # Extract the frozen thread snapshot state from the persistent Checkpointer memory
    state_snapshot = agent_app.get_state(graph_config)
    
    if state_snapshot.next and state_snapshot.next[0] == "executor":
        proposed_fix = state_snapshot.values.get("proposed_remediation")
        
        print("\n" + "🛑 "*20)
        print("       [SAFETY BOUNDARY TRIGGERED: PENDING INTERRUPT AUTHORIZATION]   ")
        print("🛑 "*20)
        print(f"\nAutonomous agent generated the following infrastructure mutation: \n>> {proposed_fix}")
        
        # Interactive secure terminal verification prompt
        user_approval = input("\nAuthorize execution of the proposed change? (Y/N): ").strip().upper()
        
        if user_approval == "Y":
            print("\n✅ Authorization granted. Resuming execution graph pipeline...")
            for event in agent_app.stream(None, graph_config):
                 for node_name, _ in event.items():
                     print(f"   [Execution Control] Node '{node_name}' completed post-approval.")
            print("\n🎉 Incident resolved autonomously. Kafka offset committed.")
        else:
            print("\n❌ Authorization explicitly denied by Operator. Freezing pipeline mutation.")
            print("🚨 Event escalated via PagerDuty to primary SRE on-call rotation. Kafka offset committed.")

if __name__ == "__main__":
    simulate_kafka_consumer()
