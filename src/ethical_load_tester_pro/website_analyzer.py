from dataclasses import dataclass
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import re
import ssl
import urllib3

@dataclass
class WebsiteTemplate:
    name: str
    type: str
    features: List[str]
    test_paths: List[str]
    required_actions: List[str]
    headers: Dict[str, str]
    auth_required: bool
    test_scenarios: List[str]
    security_requirements: Dict[str, bool]

class WebsiteAnalyzer:
    def __init__(self):
        # Initialize templates dictionary
        self.templates = {}
        
        # Configure secure requests
        self.session = requests.Session()
        self.session.verify = True
        
        # Modern headers and security settings
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }

        # Initialize all templates
        self.initialize_templates()

    def initialize_templates(self):
        """Initialize all website templates"""
        self.templates['academic'] = WebsiteTemplate(
            name='Academic Portal',
            type='academic',
            features=['login_form', 'student_portal', 'course_management'],
            test_paths=['/login', '/student', '/courses', '/portal'],
            required_actions=['login', 'view_courses', 'access_resources'],
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            auth_required=True,
            test_scenarios=['login_attempt', 'view_courses', 'access_resources'],
            security_requirements={
                'https': True,
                'hsts': True,
                'csrf_protection': True
            }
        )

        self.templates['login'] = WebsiteTemplate(
            name='Login Portal',
            type='authentication',
            features=['login_form', 'authentication'],
            test_paths=['/login', '/auth', '/signin'],
            required_actions=['login'],
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            auth_required=True,
            test_scenarios=['login_attempt', 'failed_login', 'password_reset'],
            security_requirements={
                'https': True,
                'hsts': True,
                'csrf_protection': True
            }
        )

        self.templates['ecommerce'] = WebsiteTemplate(
            name='E-commerce Site',
            type='shopping',
            features=['product_listing', 'cart', 'checkout'],
            test_paths=['/products', '/cart', '/checkout'],
            required_actions=['browse', 'add_to_cart', 'checkout'],
            headers={'Accept': 'application/json'},
            auth_required=False,
            test_scenarios=['browse_products', 'search', 'cart_operations'],
            security_requirements={
                'https': True,
                'hsts': True,
                'csrf_protection': True
            }
        )

        self.templates['blog'] = WebsiteTemplate(
            name='Blog Platform',
            type='blog',
            features=['posts', 'comments', 'categories'],
            test_paths=['/posts', '/articles', '/blog', '/feed'],
            required_actions=['view_post', 'comment', 'search'],
            headers={
                'Accept': 'text/html,application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            auth_required=False,
            test_scenarios=['view_posts', 'search_content', 'load_comments'],
            security_requirements={
                'https': True,
                'hsts': False,
                'csrf_protection': True
            }
        )

        self.templates['api'] = WebsiteTemplate(
            name='API Service',
            type='api',
            features=['rest_endpoints', 'authentication', 'rate_limiting'],
            test_paths=['/api', '/v1', '/graphql'],
            required_actions=['authenticate', 'query', 'paginate'],
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            auth_required=True,
            test_scenarios=['authentication', 'data_retrieval', 'error_handling'],
            security_requirements={
                'https': True,
                'hsts': True,
                'csrf_protection': False
            }
        )

        self.templates['social'] = WebsiteTemplate(
            name='Social Platform',
            type='social',
            features=['profiles', 'feed', 'messaging'],
            test_paths=['/feed', '/profile', '/messages'],
            required_actions=['view_feed', 'update_profile', 'send_message'],
            headers={
                'Accept': 'text/html,application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            auth_required=True,
            test_scenarios=['feed_loading', 'profile_actions', 'messaging'],
            security_requirements={
                'https': True,
                'hsts': True,
                'csrf_protection': True
            }
        )

    def analyze_security(self, url: str) -> Dict[str, bool]:
        """Analyze website security features"""
        security_features = {
            'https': url.startswith('https://'),
            'hsts': False,
            'content_security_policy': False,
            'x_frame_options': False,
            'x_content_type_options': False,
            'referrer_policy': False
        }

        try:
            response = self.session.get(url, headers=self.default_headers, timeout=10)
            headers = response.headers

            # Check security headers
            security_features.update({
                'hsts': 'Strict-Transport-Security' in headers,
                'content_security_policy': 'Content-Security-Policy' in headers,
                'x_frame_options': 'X-Frame-Options' in headers,
                'x_content_type_options': 'X-Content-Type-Options' in headers,
                'referrer_policy': 'Referrer-Policy' in headers
            })

            return security_features
        except Exception as e:
            print(f"Security analysis error: {str(e)}")
            return security_features

    def ensure_https(self, url: str) -> str:
        """Ensure URL uses HTTPS"""
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        elif url.startswith('http://'):
            url = f'https://{url[7:]}'
        return url

    def analyze_website(self, url: str) -> Optional[WebsiteTemplate]:
        """Analyze website with improved detection"""
        url = self.ensure_https(url)
        security_features = self.analyze_security(url)

        try:
            # Add timeout and error handling
            response = self.session.get(
                url, 
                headers=self.default_headers, 
                timeout=10,
                verify=False  # For handling self-signed certificates
            )
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for academic indicators
            academic_indicators = [
                'university', 'college', 'academic', 'student', 'faculty',
                'campus', 'course', 'edu', '.edu', 'srmist', 'academic'
            ]
            
            is_academic = any(ind in url.lower() for ind in academic_indicators) or \
                         any(ind in str(soup).lower() for ind in academic_indicators)

            if is_academic:
                template = self.templates['academic']
                template.security_requirements = security_features
                return template

            # Enhanced security checks for forms
            forms = soup.find_all('form')
            secure_forms = [f for f in forms if f.get('action', '').startswith('https://')]
            has_secure_forms = len(secure_forms) == len(forms)

            # Template detection with security consideration
            template = self.detect_template(soup, response, security_features)
            if template:
                template.security_requirements = security_features
                
                # Update headers based on security features
                if security_features['https']:
                    template.headers.update({
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none'
                    })

            return template

        except requests.exceptions.SSLError:
            print("SSL/TLS error - attempting with SSL verification disabled")
            return self.analyze_website_insecure(url)
        except requests.exceptions.RequestException as e:
            print(f"Error analyzing website: {str(e)}")
            return None

    def analyze_website_insecure(self, url: str) -> Optional[WebsiteTemplate]:
        """Fallback method for websites with SSL issues"""
        try:
            response = self.session.get(
                url,
                headers=self.default_headers,
                timeout=10,
                verify=False
            )
            # ... same analysis code as above ...
        except Exception as e:
            print(f"Error in insecure analysis: {str(e)}")
            return None

    def detect_template(self, soup, response, security_features) -> Optional[WebsiteTemplate]:
        """Enhanced template detection with security consideration"""
        # Check for login form
        login_form = bool(soup.find('form', {'action': re.compile(r'login|signin|auth', re.I)}))
        
        # Check for e-commerce features
        cart_elements = bool(soup.find(text=re.compile(r'cart|basket|checkout', re.I)))
        product_elements = bool(soup.find(text=re.compile(r'product|price|buy', re.I)))
        
        # Check for blog features
        blog_elements = bool(soup.find(text=re.compile(r'post|article|blog', re.I)))
        
        # Check for API endpoints
        api_elements = 'api' in url.lower() or bool(response.headers.get('Content-Type', '').startswith('application/json'))
        
        # Check for social features
        social_elements = bool(soup.find(text=re.compile(r'profile|feed|follow', re.I)))

        # Determine template type
        if login_form and not any([cart_elements, product_elements, blog_elements]):
            return self.templates['login']
        elif cart_elements and product_elements:
            return self.templates['ecommerce']
        elif blog_elements:
            return self.templates['blog']
        elif api_elements:
            return self.templates['api']
        elif social_elements:
            return self.templates['social']
        
        return None

    def get_test_configuration(self, template: WebsiteTemplate) -> dict:
        """Get test configuration based on website template"""
        config = {
            'paths_to_test': template.test_paths,
            'scenarios': template.test_scenarios,
            'headers': template.headers,
            'auth_required': template.auth_required,
            'actions': template.required_actions
        }
        
        if template.auth_required:
            config['auth_endpoints'] = ['/login', '/signin', '/auth']
            config['auth_required'] = True
            
        return config 