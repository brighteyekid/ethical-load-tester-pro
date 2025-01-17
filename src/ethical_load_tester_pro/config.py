from dataclasses import dataclass
from typing import Optional

@dataclass
class TestConfig:
    """Configuration class for load testing parameters."""
    target: str
    port: int
    protocol: str
    duration: int
    rate: int
    
    def __post_init__(self):
        # Validate target
        if not self.target:
            raise ValueError("Target cannot be empty")
        
        # Clean up target URL
        self.target = self.target.strip().lower()
        
        # Ensure protocol is supported
        if self.protocol.upper() not in ['HTTP', 'HTTPS', 'TCP', 'UDP']:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
        
        # Set default ports based on protocol
        if self.port == 80 and self.protocol.upper() == 'HTTPS':
            self.port = 443
            
        # Validate port range
        if not (0 < self.port <= 65535):
            raise ValueError(f"Invalid port number: {self.port}")
        
        # Validate duration and rate
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.rate <= 0:
            raise ValueError("Rate must be positive")
        
        # Add protocol prefix if needed
        if not self.target.startswith(('http://', 'https://')):
            prefix = 'https://' if self.protocol.upper() == 'HTTPS' else 'http://'
            self.target = f"{prefix}{self.target}" 