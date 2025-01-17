import asyncio
import aiohttp
import time
from typing import Optional, Dict
from .config import TestConfig
import ssl

class RealLoadTest:
    def __init__(self, target: str, max_users: int = 1000, ramp_up_time: int = 300,
                 template_config: dict = None):
        # Ensure target has proper URL format
        if not target.startswith(('http://', 'https://')):
            target = f'https://{target}'  # Default to HTTPS
            
        self.target = target
        self.max_users = max_users
        self.ramp_up_time = ramp_up_time
        self.template_config = template_config or {}
        self.running = False
        self.paused = False
        self.callback = None
        self.start_time = None  # Initialize start_time attribute
        
        # Initialize test stats
        self.stats = {
            'requests_sent': 0,
            'success_count': 0,
            'error_count': 0,
            'total_response_time': 0,
            'start_time': None,
            'current_users': 0,
            'current_rate': 0.0,
            'success_rate': 0.0,
            'avg_response': 0.0,
            'test_duration': 0.0,
            'progress': 0.0
        }
        
        # Add test completion flag
        self.test_completed = False
        self.target_rate = max_users  # Store target request rate
        self.last_request_time = None

    async def start(self):
        """Start the load test with improved control"""
        try:
            self.running = True
            self.test_completed = False
            self.stats['start_time'] = time.time()
            self.last_request_time = self.stats['start_time']
            
            connector = aiohttp.TCPConnector(
                limit=None,  # Remove connection limit
                force_close=False,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
            ) as session:
                while self.running and not self.test_completed:
                    current_time = time.time()
                    elapsed = current_time - self.stats['start_time']
                    
                    if elapsed >= self.ramp_up_time:
                        self.test_completed = True
                        break
                    
                    if not self.paused:
                        await self.generate_load(session)
                        
                        # Update GUI more frequently
                        if self.callback:
                            self.callback(dict(self.stats))
                    
                    # Small delay to prevent CPU overload
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            print(f"Test error: {str(e)}")
        finally:
            self.running = False
            self.test_completed = True
            # Final stats update
            if self.callback:
                self.stats['progress'] = 100
                self.callback(dict(self.stats))

    async def generate_load(self, session):
        """Generate load with precise rate control"""
        try:
            current_time = time.time()
            elapsed = current_time - self.stats['start_time']
            
            # Calculate how many requests we should have sent by now
            target_requests = int(elapsed * self.target_rate)
            actual_requests = self.stats['requests_sent']
            
            # Calculate how many requests to send in this batch
            requests_needed = max(1, min(
                target_requests - actual_requests,
                self.target_rate  # Don't exceed target rate per batch
            ))
            
            # Update current users stat
            self.stats['current_users'] = requests_needed
            
            # Send requests
            tasks = []
            for _ in range(requests_needed):
                tasks.append(self._send_request(session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress
            self.stats.update({
                'progress': min(100, (elapsed / self.ramp_up_time) * 100),
                'current_rate': self.stats['requests_sent'] / max(0.1, elapsed),
                'test_duration': elapsed
            })
            
            # Calculate delay to maintain rate
            actual_rate = self.stats['current_rate']
            if actual_rate > self.target_rate:
                await asyncio.sleep(0.05)  # Small delay if we're going too fast
            
        except Exception as e:
            print(f"Load generation error: {str(e)}")

    async def _send_request(self, session):
        """Send HTTP/HTTPS request with improved error handling and logging"""
        try:
            start_time = time.time()
            # Add timeout and SSL context
            ssl_context = ssl.create_default_context()
            async with session.get(self.target, 
                                 allow_redirects=True,
                                 timeout=30,
                                 ssl=ssl_context) as response:
                response_time = time.time() - start_time
                
                # Update stats
                self.stats['requests_sent'] += 1
                if response.status < 400:
                    self.stats['success_count'] += 1
                self.stats['total_response_time'] += response_time
                
                # Update derived stats
                total_requests = max(1, self.stats['requests_sent'])
                self.stats.update({
                    'success_rate': (self.stats['success_count'] / total_requests) * 100,
                    'avg_response': self.stats['total_response_time'] / total_requests,
                    'test_duration': time.time() - self.stats['start_time']
                })

                return response.status, response_time

        except Exception as e:
            self.stats['error_count'] += 1
            return None, time.time() - start_time

    def stop(self):
        """Stop the load test"""
        self.running = False

    def pause(self):
        """Pause the load test"""
        self.paused = True

    def resume(self):
        """Resume the load test"""
        self.paused = False

    def set_callback(self, callback):
        """Set callback for GUI updates"""
        self.callback = callback if callable(callback) else None

def main():
    test = RealLoadTest(target="example.com", max_users=1000, ramp_up_time=300)
    test.set_callback(update_gui)
    test.start()

if __name__ == "__main__":
    main()

    def update_gui(stats):
        print(f"Current users: {stats['current_users']}")
        print(f"Requests sent: {stats['requests_sent']}")
        print(f"Success rate: {stats['success_rate']:.2f}%")
        print(f"Average response time: {stats['avg_response']:.2f} seconds")
        print(f"Current rate: {stats['current_rate']:.2f} requests per second")
