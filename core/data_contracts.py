from datetime import datetime, UTC
from typing import Literal
from pydantic import BaseModel, Field

class SystemMetrics(BaseModel):
    """
    Data contract representing raw infrastructure telemetry 
    harvested directly from native host hardware sensors.
    """
    cpu_usage_percent: float = Field(..., ge=0.0, le=100.0, description="Total CPU utilization percentage.")
    memory_usage_percent: float = Field(..., ge=0.0, le=100.0, description="Total virtual memory utilization percentage.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="UTC timestamp of the collection event.")

class AlertPayload(BaseModel):
    """
    Enterprise data contract representing a standardized alert payload 
    dispatched from upstream ingestion layers to downstream orchestration networks.
    """
    alert_id: str = Field(..., description="Unique deterministic or pseudorandom identifier for the event tracing.")
    severity: Literal["INFO", "WARNING", "CRITICAL"] = Field(..., description="Log severity categorization mapping to error impact.")
    component: str = Field(default="macbook-m3-node", description="The source infrastructure boundary triggering the telemetry boundary.")
    description: str = Field(..., description="Human-readable contextual summary of the operational anomaly.")
    raw_metrics: SystemMetrics = Field(..., description="Embedded raw infrastructure telemetry mapping to the current alert state.")

    @property
    def is_actionable(self) -> bool:
        """
        Encapsulated core business rule. 
        Only WARNING and CRITICAL states are routed into the LangGraph execution pool.
        """
        return self.severity in ("WARNING", "CRITICAL")
