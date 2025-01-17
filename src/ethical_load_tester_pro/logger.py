import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json

class TestLogger:
    def __init__(self):
        self.start_time = datetime.now()
        self.requests_count = 0
        self.errors_count = 0
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        
        # Set up logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"loadtest_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log(self, message: str) -> None:
        """Log a general message."""
        self.logger.info(message)

    def log_request(self, status_code: int, response_time: float) -> None:
        """Log information about a single request with memory management"""
        self.requests_count += 1
        # Limit stored response times to prevent memory issues
        max_stored_responses = 10000
        if len(self.response_times) >= max_stored_responses:
            self.response_times = self.response_times[-(max_stored_responses//2):]
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def log_error(self, error_message: str) -> None:
        """Log an error message."""
        self.errors_count += 1
        self.logger.error(error_message)

    def generate_report(self) -> None:
        """Generate a comprehensive test report."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = [
            "\n=== Load Test Report ===",
            f"Test Duration: {duration:.2f} seconds",
            f"Total Requests: {self.requests_count}",
            f"Error Count: {self.errors_count}",
            f"Requests/Second: {self.requests_count / duration:.2f}",
            "\nResponse Time Statistics:",
            f"- Min: {min(self.response_times):.3f}s" if self.response_times else "- Min: N/A",
            f"- Max: {max(self.response_times):.3f}s" if self.response_times else "- Max: N/A",
            f"- Avg: {sum(self.response_times)/len(self.response_times):.3f}s" if self.response_times else "- Avg: N/A",
            "\nStatus Code Distribution:"
        ]
        
        for status_code, count in self.status_codes.items():
            report.append(f"- {status_code}: {count} ({count/self.requests_count*100:.1f}%)")
        
        # Add infrastructure details if available
        if hasattr(self, 'infrastructure_details'):
            report.append("\nInfrastructure Analysis:")
            
            # Server Details
            server = self.infrastructure_details.get('server', {})
            report.append("\nServer Configuration:")
            report.append(f"- Signatures: {', '.join(server.get('signatures', []))}")
            report.append(f"- Technologies: {', '.join(server.get('technologies', []))}")
            report.append(f"- Capabilities: {', '.join(server.get('capabilities', []))}")
            
            # Load Balancer Details
            lb = self.infrastructure_details.get('load_balancer', {})
            report.append("\nLoad Balancer Configuration:")
            report.append(f"- Detected IPs: {', '.join(lb.get('ips', []))}")
            report.append("- Load Balancer Headers:")
            for header, value in lb.get('headers', {}).items():
                report.append(f"  • {header}: {value}")
            
            # Security Details
            security = self.infrastructure_details.get('security', {})
            report.append("\nSecurity Configuration:")
            if security.get('ssl'):
                ssl_info = security['ssl']
                report.append(f"- SSL Protocol: {ssl_info.get('protocol_version', 'Unknown')}")
                report.append(f"- SSL Expiry: {ssl_info.get('valid_until', 'Unknown')}")
            report.append(f"- Security Headers: {', '.join(security.get('security_headers', []))}")
        
        self.log("\n".join(report)) 

    def log_rate_limit_info(self, headers: dict):
        """Log information about rate limiting headers."""
        rate_limit_info = [
            "\nRate Limiting Information:",
            f"Retry-After: {headers.get('Retry-After', 'Not specified')}",
            f"X-RateLimit-Limit: {headers.get('X-RateLimit-Limit', 'Not specified')}",
            f"X-RateLimit-Remaining: {headers.get('X-RateLimit-Remaining', 'Not specified')}",
            f"X-RateLimit-Reset: {headers.get('X-RateLimit-Reset', 'Not specified')}"
        ]
        self.log("\n".join(rate_limit_info)) 