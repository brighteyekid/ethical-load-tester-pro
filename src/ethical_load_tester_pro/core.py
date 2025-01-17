import asyncio
import time
import aiohttp
from typing import List
from .lb_detector import LoadBalancerDetector
from .logger import TestLogger
from .config import TestConfig
from .protocols import TCPProtocol, UDPProtocol
from .visualizer import ResultVisualizer

class LoadTester:
    def __init__(self, config: TestConfig, logger: TestLogger):
        self.config = config
        self.target = config.target
        self.logger = logger
        self.start_time = None
        self.lb_detector = LoadBalancerDetector()
        self.running = False
        self.protocol_handlers = {
            'tcp': TCPProtocol(),
            'udp': UDPProtocol(),
            'http': self._send_http_request,
            'https': self._send_http_request
        }
        self.visualizer = ResultVisualizer()
        self.request_timestamps = []
        self.callback = None
        self.stats = {
            'requests_sent': 0,
            'success_count': 0,
            'total_response_time': 0,
            'start_time': None
        }
        
        # Add client session kwargs
        self.client_session_kwargs = {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # Add new configuration options
        self.traffic_patterns = {
            'steady': self._generate_steady_load,
            'spike': self._generate_spike_load,
            'gradual': self._generate_gradual_load,
            'flash_sale': self._generate_flash_sale_load
        }
        
        # Add connection simulation options
        self.connection_types = {
            'normal': {'latency': 0, 'bandwidth': None},
            'slow_3g': {'latency': 100, 'bandwidth': 50000},  # 50 KB/s
            'fast_3g': {'latency': 50, 'bandwidth': 250000},  # 250 KB/s
            'slow_dsl': {'latency': 30, 'bandwidth': 512000}  # 512 KB/s
        }
        
        # Add safety thresholds
        self.safety_thresholds = {
            'max_error_rate': 0.2,  # 20% error rate
            'max_response_time': 5.0,  # 5 seconds
            'min_success_rate': 0.8,  # 80% success rate
        }

    def stop(self):
        """Stop the load test"""
        self.running = False
        self.logger.log("Test stopped by user")

    async def _generate_http_load(self):
        """Generate HTTP load using aiohttp."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, force_close=False)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        ) as session:
            while self.running:
                if time.time() - self.start_time >= self.config.duration:
                    break
                
                tasks = []
                for _ in range(self.config.rate):
                    tasks.append(self._send_http_request(session))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(1)  # Wait for next batch

    async def _send_http_request(self, session):
        """Send HTTP/HTTPS request with improved error handling and logging"""
        try:
            start_time = time.time()
            async with session.get(self.target, allow_redirects=True) as response:
                await response.read()
                response_time = time.time() - start_time
                
                # Log the request in the logger
                self.logger.log_request(response.status, response_time)
                
                # Update stats
                self.stats['requests_sent'] += 1
                if response.status < 400:
                    self.stats['success_count'] += 1
                self.stats['total_response_time'] += response_time
                
                # Store timestamp for visualization
                self.request_timestamps.append(time.time() - self.start_time)
                
                # Analyze response for load balancer detection
                self.lb_detector.analyze_response(response)
                
                # Send real-time update
                if self.callback:
                    try:
                        current_stats = {
                            'timestamp': time.time() - self.start_time,
                            'response_time': response_time,
                            'status_code': response.status,
                            'requests_sent': self.stats['requests_sent'],
                            'success_rate': (self.stats['success_count'] / self.stats['requests_sent']) * 100,
                            'avg_response': self.stats['total_response_time'] / self.stats['requests_sent'],
                            'current_rate': self.stats['requests_sent'] / (time.time() - self.start_time)
                        }
                        self.callback(current_stats)
                    except Exception as e:
                        self.logger.log_error(f"Callback error: {str(e)}")
                
                return response.status, response_time
                
        except Exception as e:
            error_msg = str(e)
            self.logger.log_error(f"Request error: {error_msg}")
            self.stats['requests_sent'] += 1  # Count failed requests too
            
            # Send error update to callback
            if self.callback:
                try:
                    current_stats = {
                        'timestamp': time.time() - self.start_time,
                        'response_time': time.time() - start_time,
                        'status_code': 0,
                        'requests_sent': self.stats['requests_sent'],
                        'success_rate': (self.stats['success_count'] / self.stats['requests_sent']) * 100,
                        'avg_response': self.stats['total_response_time'] / max(1, self.stats['requests_sent']),
                        'current_rate': self.stats['requests_sent'] / (time.time() - self.start_time)
                    }
                    self.callback(current_stats)
                except Exception as callback_error:
                    self.logger.log_error(f"Callback error: {str(callback_error)}")
            
            return None, time.time() - start_time

    async def _generate_protocol_load(self):
        """Generate load for TCP/UDP protocols."""
        protocol_handler = self.protocol_handlers[self.config.protocol]
        while self.running:
            if time.time() - self.start_time >= self.config.duration:
                break
            
            tasks = []
            for _ in range(self.config.rate):
                tasks.append(self._send_protocol_request(protocol_handler))
            
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)

    async def _send_protocol_request(self, protocol_handler):
        """Send a single TCP/UDP request and log the result."""
        try:
            result = await protocol_handler.send_request(
                self.config.target, 
                self.config.port
            )
            
            self.request_timestamps.append(time.time() - self.start_time)
            if result.success:
                self.logger.log_request(200, result.response_time)
            else:
                self.logger.log_error(result.error)
        except Exception as e:
            self.logger.log_error(str(e))

    async def generate_load(self):
        """Generate load with proper SSL configuration and error handling"""
        try:
            connector = aiohttp.TCPConnector(verify_ssl=False, limit=100)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.client_session_kwargs['headers']
            ) as session:
                self.running = True
                self.start_time = time.time()
                
                # Rate limiting control
                rate_limit_delay = 1.0  # Start with 1 second delay
                consecutive_429s = 0
                
                while self.running:
                    if time.time() - self.start_time >= self.config.duration:
                        break
                    
                    # Create batch of requests with adjusted rate
                    adjusted_rate = max(1, self.config.rate // (2 ** consecutive_429s))
                    tasks = []
                    for _ in range(adjusted_rate):
                        tasks.append(asyncio.ensure_future(self._send_http_request(session)))
                    
                    # Wait for all requests in batch to complete
                    try:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Check for rate limiting
                        rate_limited = sum(1 for r in results if isinstance(r, tuple) and r[0] == 429)
                        
                        if rate_limited > 0:
                            consecutive_429s = min(consecutive_429s + 1, 5)  # Cap at 32x reduction
                            rate_limit_delay *= 1.5  # Increase delay
                            self.logger.log(f"Rate limited, reducing request rate to {adjusted_rate}/s")
                            await asyncio.sleep(rate_limit_delay)
                        else:
                            consecutive_429s = max(0, consecutive_429s - 1)  # Recover gradually
                            rate_limit_delay = max(1.0, rate_limit_delay * 0.8)  # Decrease delay
                        
                    except Exception as e:
                        self.logger.log_error(f"Batch error: {str(e)}")
                    
                    # Log progress
                    elapsed = time.time() - self.start_time
                    self.logger.log(f"Progress: {elapsed:.1f}s / {self.config.duration}s, "
                                  f"Requests sent: {self.stats['requests_sent']}")
                    
                    # Dynamic rate limiting delay
                    await asyncio.sleep(rate_limit_delay)

        except Exception as e:
            self.logger.log_error(f"Load generation error: {str(e)}")
        finally:
            self.running = False

    def run(self):
        """Start the load test."""
        self.running = True
        self.start_time = time.time()
        self.logger.log(f"Starting load test against {self.config.target}")
        
        # Run the async event loop
        asyncio.run(self.generate_load())
        
        # Generate final report
        self.generate_report()

    def cleanup(self):
        """Clean up resources and stop the test."""
        self.running = False
        self.logger.log("Test completed. Cleaning up resources...")

    def generate_report(self):
        """Generate comprehensive test report including visualizations."""
        self.logger.generate_report()
        lb_report = self.lb_detector.generate_report()
        self.logger.log("Load Balancer Analysis:")
        self.logger.log(lb_report)
        
        # Generate visualizations if we have data
        if self.request_timestamps:
            try:
                response_time_plot = self.visualizer.create_response_time_plot(
                    self.logger.response_times,
                    self.config.duration
                )
                status_plot = self.visualizer.create_status_code_plot(
                    self.logger.status_codes
                )
                timeline_plot = self.visualizer.create_requests_timeline(
                    self.request_timestamps,
                    self.logger.response_times
                )
                
                self.logger.log("\nGenerated visualization reports:")
                self.logger.log(f"Response time distribution: {response_time_plot}")
                self.logger.log(f"Status code distribution: {status_plot}")
                self.logger.log(f"Request timeline: {timeline_plot}")
            except Exception as e:
                self.logger.log(f"Warning: Could not generate visualizations: {str(e)}") 

    def set_callback(self, callback):
        """Set callback function for real-time updates"""
        self.callback = callback 

    async def _generate_spike_load(self):
        """Simulate sudden traffic spikes"""
        base_rate = self.config.rate
        spike_multiplier = 5
        spike_duration = 30  # seconds 

    async def _check_safety_thresholds(self, stats):
        """Monitor and enforce safety thresholds"""
        if stats['error_rate'] > self.safety_thresholds['max_error_rate']:
            self.logger.log_warning("High error rate detected - reducing load")
            await self._reduce_load_rate() 