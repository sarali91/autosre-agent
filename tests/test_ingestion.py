import pytest
from unittest.mock import patch, MagicMock
from ingestion.metrics_scraper import MacMetricsScraper
from core.data_contracts import SystemMetrics, AlertPayload

class TestMacMetricsScraper:
    """
    Test suite for the hardware ingestion layer.
    Ensures metrics are scraped correctly and Pydantic data contracts are respected.
    """

    def setup_method(self):
        """Initialize the scraper with strict thresholds before each test."""
        self.scraper = MacMetricsScraper(cpu_threshold=80.0, mem_threshold=90.0)

    @patch("ingestion.metrics_scraper.psutil")
    def test_scraper_generates_critical_alert_on_high_cpu(self, mock_psutil: MagicMock):
        """
        Validates that a CPU spike triggers a CRITICAL actionable alert
        and conforms to the AlertPayload schema.
        """
        # 1. Arrange: Mock the hardware sensors returning high usage
        mock_psutil.cpu_percent.return_value = 95.0
        
        mock_mem = MagicMock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        # 2. Act: Execute the ingestion logic
        alert: AlertPayload = self.scraper.generate_alert()

        # 3. Assert: Validate the data flow and business logic
        assert alert.severity == "CRITICAL"
        assert alert.is_actionable is True
        assert alert.raw_metrics.cpu_usage_percent == 95.0
        assert "Resource exhaustion detected" in alert.description

    @patch("ingestion.metrics_scraper.psutil")
    def test_scraper_generates_info_alert_on_normal_load(self, mock_psutil: MagicMock):
        """
        Validates that normal hardware metrics result in an INFO alert
        that is flagged as non-actionable (dropped before hitting the graph).
        """
        # 1. Arrange: Mock normal system behavior
        mock_psutil.cpu_percent.return_value = 15.0
        
        mock_mem = MagicMock()
        mock_mem.percent = 45.0
        mock_psutil.virtual_memory.return_value = mock_mem

        # 2. Act: Execute the ingestion logic
        alert: AlertPayload = self.scraper.generate_alert()

        # 3. Assert: Validate the data flow
        assert alert.severity == "INFO"
        assert alert.is_actionable is False
        assert alert.raw_metrics.cpu_usage_percent == 15.0
        assert "healthy operational baseline" in alert.description
