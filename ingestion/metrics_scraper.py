import logging
import uuid
from typing import Literal
import psutil

from core.data_contracts import SystemMetrics, AlertPayload

logger = logging.getLogger(__name__)

class MacMetricsScraper:
    """
    Upstream ingestion gateway service responsible for scraping real-time telemetry 
    from host system architectures and sanitizing them into strongly-typed objects.
    """
    def __init__(self, cpu_threshold: float = 80.0, mem_threshold: float = 90.0):
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold

    def scrape_real_data(self) -> SystemMetrics:
        """
        Harvests actual system footprints natively from macOS.
        Enforces a 0.5-second blocking interval to accurately calculate delta CPU utilization.
        """
        logger.info("Executing stateless hardware scraping sequence via psutil sensors...")
        
        # Blocking interval required to calculate accurate CPU usage percentages
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        
        return SystemMetrics(
            cpu_usage_percent=cpu,
            memory_usage_percent=mem
        )

    def generate_alert(self) -> AlertPayload:
        """
        Ingests real-time hardware metrics, evaluates thresholds, 
        and constructs a validated AlertPayload instance for downstream consumers.
        """
        metrics = self.scrape_real_data()
        severity: Literal["INFO", "CRITICAL"] = "INFO"
        description = "System metrics are within healthy operational baseline boundaries."

        # Threshold breaching logic evaluating real scraped data
        if metrics.cpu_usage_percent > self.cpu_threshold or metrics.memory_usage_percent > self.mem_threshold:
            severity = "CRITICAL"
            description = (
                f"Resource exhaustion detected! Host metrics exceeded target SLA. "
                f"CPU Utilization: {metrics.cpu_usage_percent}%, Memory Utilization: {metrics.memory_usage_percent}%"
            )
            logger.warning(f"Inbound alert constraint violated: {description}")

        return AlertPayload(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            severity=severity,
            description=description,
            raw_metrics=metrics
        )
