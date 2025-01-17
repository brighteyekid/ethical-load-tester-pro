import re
import socket
import ssl
import requests
import dns.resolver
import whois
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set
import statistics

class LoadBalancerDetector:
    def __init__(self):
        # Core detection attributes
        self.server_signatures: Set[str] = set()
        self.ip_addresses: Set[str] = set()
        self.response_headers = defaultdict(set)
        self.response_times: List[float] = []
        
        # Enhanced detection attributes
        self.ssl_info: Dict = {}
        self.server_tech: Set[str] = set()
        self.dns_records: Dict = {}
        self.whois_info = None
        self.server_capabilities: Set[str] = set()
        self.rate_limit_info: Dict = {}
        
        # Common load balancer signatures
        self.lb_headers = {
            'x-lb': 'Generic Load Balancer',
            'x-varnish': 'Varnish Cache',
            'x-cache': 'Caching Layer',
            'x-served-by': 'Server Farm',
            'x-timer': 'Request Timing',
            'x-cdn': 'CDN Information',
            'via': 'Proxy Information',
            'x-amz-cf-id': 'AWS CloudFront',
            'x-azure-ref': 'Azure Front Door',
            'x-cloud-trace-context': 'Google Cloud',
            'cf-ray': 'Cloudflare',
            'server-timing': 'Performance Metrics',
            'x-runtime': 'Application Runtime'
        }
        
        # Add advanced detection capabilities
        self.response_patterns = defaultdict(list)
        self.server_fingerprints = set()
        self.timing_analysis = []

    def analyze_target(self, target: str) -> None:
        """Perform comprehensive target analysis"""
        try:
            # DNS Analysis
            self._analyze_dns(target)
            
            # SSL/TLS Analysis
            self._analyze_ssl(target)
            
            # WHOIS Information
            self._analyze_whois(target)
            
            # Server Capabilities
            self._analyze_server_capabilities(target)
            
        except Exception as e:
            print(f"Error during target analysis: {str(e)}")

    def _analyze_dns(self, target: str) -> None:
        """Analyze DNS records"""
        try:
            domain = target.split('://')[1].split('/')[0]
            
            # Get various DNS records
            record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS']
            for record_type in record_types:
                try:
                    answers = dns.resolver.resolve(domain, record_type)
                    self.dns_records[record_type] = [str(rdata) for rdata in answers]
                except Exception:
                    continue
                    
            # Check for GeoDNS
            try:
                answers = dns.resolver.resolve(domain, 'A')
                if len(set(str(rdata) for rdata in answers)) > 1:
                    self.server_capabilities.add('GeoDNS')
            except Exception:
                pass
                
        except Exception as e:
            print(f"DNS analysis error: {str(e)}")

    def _analyze_ssl(self, target: str) -> None:
        """Analyze SSL/TLS configuration"""
        try:
            if not target.startswith('https'):
                return
                
            domain = target.split('://')[1].split('/')[0]
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443)) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    self.ssl_info = {
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'subject': dict(x[0] for x in cert['subject']),
                        'version': cert['version'],
                        'valid_from': cert['notBefore'],
                        'valid_until': cert['notAfter'],
                        'protocol_version': ssock.version()
                    }
        except Exception as e:
            print(f"SSL analysis error: {str(e)}")

    def _analyze_whois(self, target: str) -> None:
        """Get WHOIS information"""
        try:
            domain = target.split('://')[1].split('/')[0]
            self.whois_info = whois.whois(domain)
        except Exception as e:
            print(f"WHOIS analysis error: {str(e)}")

    def _analyze_server_capabilities(self, target: str) -> None:
        """Analyze server capabilities and technologies"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; SecurityAnalyzer/1.0)'
            }
            
            # Test HTTP/2 support
            try:
                response = requests.get(target, headers=headers)
                if response.raw.version == 20:
                    self.server_capabilities.add('HTTP/2')
            except:
                pass
                
            # Test compression
            headers['Accept-Encoding'] = 'gzip, deflate'
            try:
                response = requests.get(target, headers=headers)
                if response.headers.get('content-encoding'):
                    self.server_capabilities.add(f"Compression: {response.headers['content-encoding']}")
            except:
                pass
                
            # Check security headers
            security_headers = [
                'strict-transport-security',
                'content-security-policy',
                'x-frame-options',
                'x-xss-protection'
            ]
            
            response = requests.get(target, headers=headers)
            for header in security_headers:
                if header in response.headers:
                    self.server_capabilities.add(f"Security: {header}")
                    
        except Exception as e:
            print(f"Server capabilities analysis error: {str(e)}")

    def _analyze_rate_limits(self, headers: Dict) -> None:
        """Analyze rate limiting headers"""
        rate_limit_headers = [
            'x-ratelimit-limit',
            'x-ratelimit-remaining',
            'x-ratelimit-reset',
            'retry-after'
        ]
        
        for header in rate_limit_headers:
            if header in headers:
                self.rate_limit_info[header] = headers[header]

    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        report = ["\n=== Infrastructure Analysis Report ===\n"]
        
        # Load Balancer Detection
        report.append("Load Balancer Analysis:")
        report.append(f"Unique IP addresses detected: {len(self.ip_addresses)}")
        if self.ip_addresses:
            report.append("IPs: " + ", ".join(self.ip_addresses))
        
        report.append(f"\nUnique server signatures: {len(self.server_signatures)}")
        if self.server_signatures:
            report.append("Signatures: " + ", ".join(self.server_signatures))
        
        # Load Balancer Headers
        report.append("\nLoad balancer indicators:")
        for header, values in self.response_headers.items():
            if header in self.lb_headers:
                report.append(f"- {header}: {', '.join(values)} ({self.lb_headers[header]})")
        
        # DNS Information
        if self.dns_records:
            report.append("\nDNS Configuration:")
            for record_type, records in self.dns_records.items():
                report.append(f"- {record_type} Records: {', '.join(records)}")
        
        # SSL/TLS Information
        if self.ssl_info:
            report.append("\nSSL/TLS Configuration:")
            report.append(f"- Protocol: {self.ssl_info.get('protocol_version', 'Unknown')}")
            report.append(f"- Valid Until: {self.ssl_info.get('valid_until', 'Unknown')}")
            report.append(f"- Issuer: {self.ssl_info.get('issuer', {}).get('commonName', 'Unknown')}")
        
        # Server Capabilities
        if self.server_capabilities:
            report.append("\nServer Capabilities:")
            for capability in sorted(self.server_capabilities):
                report.append(f"- {capability}")
        
        # Rate Limiting
        if self.rate_limit_info:
            report.append("\nRate Limiting Configuration:")
            for header, value in self.rate_limit_info.items():
                report.append(f"- {header}: {value}")
        
        # Performance Metrics
        if self.response_times:
            report.append("\nBackend Performance:")
            report.append(f"- Min Response Time: {min(self.response_times):.3f}s")
            report.append(f"- Max Response Time: {max(self.response_times):.3f}s")
            report.append(f"- Avg Response Time: {sum(self.response_times)/len(self.response_times):.3f}s")
        
        # Infrastructure Assessment
        report.append("\nInfrastructure Assessment:")
        if len(self.ip_addresses) > 1:
            report.append("- Multiple backend servers detected (Load Balanced)")
        if 'GeoDNS' in self.server_capabilities:
            report.append("- Geographic distribution detected")
        if any('cache' in h.lower() for h in self.response_headers.keys()):
            report.append("- Caching layer detected")
        
        return "\n".join(report) 

    def analyze_response(self, response) -> None:
        """Analyze HTTP response for load balancer indicators."""
        try:
            # Check server headers
            if 'Server' in response.headers:
                self.server_signatures.add(response.headers['Server'])
            
            # Store response headers for analysis
            for header, value in response.headers.items():
                self.response_headers[header].add(value)
                
                # Check for load balancer specific headers
                if header.lower() in [h.lower() for h in self.lb_headers]:
                    self.server_capabilities.add(f"LoadBalancer: {self.lb_headers[header]}")
            
            # Check for compression
            if 'Content-Encoding' in response.headers:
                self.server_capabilities.add(f"Compression: {response.headers['Content-Encoding']}")
            
            # Check for security headers
            security_headers = ['Strict-Transport-Security', 'X-Frame-Options', 
                              'X-XSS-Protection', 'X-Content-Type-Options']
            for header in security_headers:
                if header in response.headers:
                    self.server_capabilities.add(f"Security: {header.lower()}")
            
            # Store rate limiting info if present
            rate_limit_headers = ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 
                                'X-RateLimit-Reset', 'Retry-After']
            for header in rate_limit_headers:
                if header in response.headers:
                    self.rate_limit_info[header] = response.headers[header]
                
        except Exception as e:
            print(f"Error analyzing response: {str(e)}") 

    def analyze_load_distribution(self):
        """Analyze load balancer distribution patterns"""
        distribution = {}
        for server_id in self.server_fingerprints:
            count = len([r for r in self.response_patterns[server_id]])
            distribution[server_id] = {
                'request_count': count,
                'avg_response_time': statistics.mean(self.response_patterns[server_id]),
                'distribution_percentage': count / len(self.timing_analysis) * 100
            }
        return distribution 