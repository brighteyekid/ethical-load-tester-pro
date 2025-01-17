#!/usr/bin/env python3
"""
EthicalLoadTesterPro - A responsible load testing tool for authorized system administrators.
"""
import argparse
import sys
from .gui import launch_gui
from .core import LoadTester
from .logger import TestLogger
from .config import TestConfig

def parse_arguments():
    parser = argparse.ArgumentParser(description="Ethical Load Testing Tool")
    parser.add_argument("--gui", action="store_true", help="Launch GUI mode")
    parser.add_argument("--target", help="Target URL or IP address")
    parser.add_argument("--port", type=int, default=80, help="Target port (default: 80)")
    parser.add_argument("--protocol", choices=['http', 'tcp', 'udp'], default='http',
                        help="Protocol to use for testing")
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration in seconds (default: 60)")
    parser.add_argument("--rate", type=int, default=100,
                        help="Requests per second (default: 100)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    if args.gui:
        launch_gui()
        return
    
    # CLI mode
    if not args.target:
        print("Error: --target is required in CLI mode")
        sys.exit(1)
    
    # Initialize logger
    logger = TestLogger()
    
    # Create test configuration
    config = TestConfig(
        target=args.target,
        port=args.port,
        protocol=args.protocol,
        duration=args.duration,
        rate=args.rate
    )
    
    # Initialize and run load tester
    tester = LoadTester(config, logger)
    try:
        tester.run()
    except KeyboardInterrupt:
        logger.log("Test interrupted by user")
    except Exception as e:
        logger.log(f"Error during test: {str(e)}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 