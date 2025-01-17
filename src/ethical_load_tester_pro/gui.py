import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from .config import TestConfig
from .core import LoadTester
from .logger import TestLogger
from .real_test import RealLoadTest
from .website_analyzer import WebsiteAnalyzer
from .visualizer import ResultVisualizer
from .consent import get_user_consent
import time
import asyncio

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        
    def write(self, string):
        # Use after() to schedule text updates on main thread
        self.text_widget.after(0, self._write, string)
        
    def _write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        
    def flush(self):
        pass

class RealTimeGraph:
    def __init__(self, parent, title="Response Times"):
        # Create figure and axis
        self.fig = Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)
        
        # Initialize data
        self.times = []
        self.values = []
        self.line = None
        self.title = title
        
        # Configure axis
        self.ax.set_title(title)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Response Time (s)' if 'Response' in title else 'Requests/s')
        self.ax.grid(True)
        
        # Set initial view range with different scales for different graphs
        self.ax.set_xlim(0, 30)
        if 'Response' in title:
            self.ax.set_ylim(0, 2)  # Response time scale 0-2 seconds
        else:
            self.ax.set_ylim(0, 10)  # Request rate scale 0-10 req/s
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().grid(sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initialize the plot line
        self.line, = self.ax.plot([], [], '-')

    def update(self, stats):
        """Update graph with new data"""
        try:
            current_time = stats['test_duration']
            
            # Determine which value to plot based on graph type
            if 'Response' in self.title:
                value = stats['avg_response']
            else:  # Request Rate graph
                value = stats['current_rate']
            
            # Append new data
            self.times.append(current_time)
            self.values.append(value)
            
            # Update line data
            self.line.set_data(self.times, self.values)
            
            # Adjust y-axis limits dynamically
            if self.values:
                ymin = 0
                ymax = max(max(self.values) * 1.2, 0.1)  # Add 20% padding and ensure non-zero
                self.ax.set_ylim(ymin, ymax)
            
            # Adjust x-axis limits if needed
            if current_time > self.ax.get_xlim()[1]:
                self.ax.set_xlim(0, current_time * 1.2)
            
            # Redraw the canvas
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Error updating graph: {str(e)}")

class LoadTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ethical Load Tester Pro")
        self.test = None
        self.test_start_time = None
        self.current_test = None
        self.updating_graph = False
        
        # Initialize status variables
        self.status_vars = {
            'Requests Sent': tk.StringVar(value="0"),
            'Success Rate': tk.StringVar(value="0%"),
            'Avg Response': tk.StringVar(value="0.000s"),
            'Current Rate': tk.StringVar(value="0.0/s")
        }
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.test_tab = ttk.Frame(self.notebook)
        self.analysis_tab = ttk.Frame(self.notebook)
        self.reports_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.test_tab, text='Load Test')
        self.notebook.add(self.analysis_tab, text='Analysis')
        self.notebook.add(self.reports_tab, text='Reports')
        
        # Create tab contents
        self.create_test_tab(self.test_tab)
        
        # Add progress variable initialization
        self.progress_var = tk.DoubleVar(value=0)
        self.current_test = None
        self.website_analyzer = WebsiteAnalyzer()

    def create_gui(self):
        # Add tabs for different features
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Main test tab
        test_frame = ttk.Frame(self.notebook)
        self.notebook.add(test_frame, text="Load Test")
        self.create_test_tab(test_frame)
        
        # Analysis tab
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="Analysis")
        self.create_analysis_tab(analysis_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="Reports")
        self.create_reports_tab(reports_frame)

    def create_analysis_tab(self, parent):
        # Website analysis section
        analysis_frame = ttk.LabelFrame(parent, text="Website Analysis", padding="5")
        analysis_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        ttk.Label(analysis_frame, text="Target URL:").grid(row=0, column=0, padx=5, pady=5)
        self.analysis_url = ttk.Entry(analysis_frame, width=40)
        self.analysis_url.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(analysis_frame, text="Analyze", command=self.analyze_website).grid(
            row=1, column=0, columnspan=3, pady=10)
        
        # Results section
        self.analysis_text = scrolledtext.ScrolledText(analysis_frame, height=10, width=50)
        self.analysis_text.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)

    def create_reports_tab(self, parent):
        reports_frame = ttk.LabelFrame(parent, text="Test Reports", padding="5")
        reports_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Graphs section
        self.fig_response = Figure(figsize=(6, 4))
        self.canvas_response = FigureCanvasTkAgg(self.fig_response, reports_frame)
        self.canvas_response.get_tk_widget().grid(row=0, column=0, padx=5, pady=5)
        
        self.fig_status = Figure(figsize=(6, 4))
        self.canvas_status = FigureCanvasTkAgg(self.fig_status, reports_frame)
        self.canvas_status.get_tk_widget().grid(row=0, column=1, padx=5, pady=5)

    def analyze_website(self):
        """Analyze the target website"""
        url = self.analysis_url.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL to analyze")
            return
            
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, "Analyzing website...\n")
        
        def run_analysis():
            try:
                template = self.website_analyzer.analyze_website(url)
                security = self.website_analyzer.analyze_security(url)
                
                self.root.after(0, lambda: self._update_analysis_results(template, security))
            except Exception as e:
                self.root.after(0, lambda: self.analysis_text.insert(tk.END, f"Error: {str(e)}\n"))
        
        threading.Thread(target=run_analysis).start()

    def _update_analysis_results(self, template, security):
        """Update analysis results in GUI"""
        self.analysis_text.delete(1.0, tk.END)
        
        if template:
            self.analysis_text.insert(tk.END, f"Website Type: {template.name}\n")
            self.analysis_text.insert(tk.END, f"Features: {', '.join(template.features)}\n")
            self.analysis_text.insert(tk.END, f"Auth Required: {template.auth_required}\n\n")
        
        self.analysis_text.insert(tk.END, "Security Analysis:\n")
        for feature, enabled in security.items():
            self.analysis_text.insert(tk.END, f"- {feature}: {'✓' if enabled else '✗'}\n")

    def start_test(self):
        """Start the load test"""
        # Get configuration from GUI inputs
        target = self.target_entry.get()
        protocol = self.protocol_var.get()
        port = int(self.port_entry.get())
        duration = int(self.duration_entry.get())
        rate = int(self.rate_entry.get())

        # Create test configuration
        config = TestConfig(
            target=target,
            port=port,
            protocol=protocol.lower(),
            duration=duration,
            rate=rate
        )

        # Initialize and start the test
        self.current_test = RealLoadTest(
            target=target,
            max_users=rate,
            ramp_up_time=duration
        )
        
        # Set the callback for real-time updates
        self.current_test.set_callback(self._update_stats_gui)
        
        # Reset progress and stats
        self.progress_var.set(0)
        for var in self.status_vars.values():
            var.set("0")

        def run_test():
            asyncio.run(self.current_test.start())

        # Start test in separate thread
        threading.Thread(target=run_test, daemon=True).start()

    def stop_test(self):
        """Stop the current test"""
        if self.current_test:
            self.current_test.stop()
            self.updating_graph = False
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)

    def pause_test(self):
        """Pause the current test"""
        if self.current_test:
            self.current_test.pause()

    def resume_test(self):
        """Resume the current test"""
        if self.current_test:
            self.current_test.resume()

    def update_stats(self, stats):
        """Update GUI stats safely from any thread"""
        if not self.root or not self.updating_graph:
            return
            
        self.root.after(0, self._update_stats_gui, stats)
        
        # Update graphs with current time and values
        if self.test_start_time:
            current_time = time.time() - self.test_start_time
            if hasattr(self, 'response_graph'):
                self.response_graph.update(current_time, stats.get('avg_response', 0))
            if hasattr(self, 'rate_graph'):
                self.rate_graph.update(current_time, stats.get('current_rate', 0))
        
    def _update_stats_gui(self, stats):
        """Update GUI with test statistics using batch updates"""
        try:
            # Batch updates to reduce GUI overhead
            self.root.update_idletasks()
            if time.time() - self._last_update > 0.1:  # Update max 10 times per second
                # Update status variables
                for var_name, value in stats.items():
                    if var_name in self.status_vars:
                        self.status_vars[var_name].set(value)
                self._last_update = time.time()
        except Exception as e:
            print(f"Error updating GUI: {str(e)}")

    def create_test_tab(self, parent):
        """Create the load test configuration tab"""
        # Test Configuration frame
        config_frame = ttk.LabelFrame(parent, text="Test Configuration", padding="5")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Target input
        ttk.Label(config_frame, text="Target:").grid(row=0, column=0, padx=5, pady=5)
        self.target_entry = ttk.Entry(config_frame, width=40)
        self.target_entry.grid(row=0, column=1, columnspan=3, sticky='w', padx=5)
        
        # Protocol selection
        ttk.Label(config_frame, text="Protocol:").grid(row=1, column=0, padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="HTTPS")
        https_radio = ttk.Radiobutton(config_frame, text="HTTPS", variable=self.protocol_var, 
                                     value="HTTPS", command=self.update_port)
        http_radio = ttk.Radiobutton(config_frame, text="HTTP", variable=self.protocol_var, 
                                    value="HTTP", command=self.update_port)
        https_radio.grid(row=1, column=1, padx=5)
        http_radio.grid(row=1, column=2, padx=5)
        
        # Port input
        ttk.Label(config_frame, text="Port:").grid(row=2, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame, width=10)
        self.port_entry.insert(0, "443")
        self.port_entry.grid(row=2, column=1, sticky='w', padx=5)
        
        # Duration input
        ttk.Label(config_frame, text="Duration (s):").grid(row=2, column=2, padx=5, pady=5)
        self.duration_entry = ttk.Entry(config_frame, width=10)
        self.duration_entry.insert(0, "10")
        self.duration_entry.grid(row=2, column=3, sticky='w', padx=5)
        
        # Rate input
        ttk.Label(config_frame, text="Rate (req/s):").grid(row=3, column=0, padx=5, pady=5)
        self.rate_entry = ttk.Entry(config_frame, width=10)
        self.rate_entry.insert(0, "10")
        self.rate_entry.grid(row=3, column=1, sticky='w', padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Test", command=self.start_test)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Test", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(parent, text="Test Progress", padding="5")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Stats display
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        row = 0
        col = 0
        for label, var in self.status_vars.items():
            ttk.Label(stats_frame, text=f"{label}:").grid(row=row, column=col*2, padx=5, pady=2)
            ttk.Label(stats_frame, textvariable=var).grid(row=row, column=col*2+1, padx=5, pady=2)
            col += 1
            if col > 1:
                col = 0
                row += 1
        
        # Real-time graphs frame
        graphs_frame = ttk.Frame(parent)
        graphs_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create and add graphs using grid
        self.response_graph = RealTimeGraph(graphs_frame, "Response Times")
        self.response_graph.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.rate_graph = RealTimeGraph(graphs_frame, "Request Rate")
        self.rate_graph.canvas.get_tk_widget().grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for graphs
        graphs_frame.grid_columnconfigure(0, weight=1)
        graphs_frame.grid_columnconfigure(1, weight=1)
        graphs_frame.grid_rowconfigure(0, weight=1)

    def update_port(self):
        """Update port based on protocol selection"""
        if self.protocol_var.get() == "HTTPS":
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, "443")  # Remove quotes
        else:
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, "80")   # Remove quotes

    def create_monitoring_tab(self, parent):
        """Create real-time monitoring dashboard"""
        monitoring_frame = ttk.LabelFrame(parent, text="Live Monitoring")
        
        # Add real-time graphs
        self.response_graph = RealTimeGraph(monitoring_frame, "Response Times")
        self.error_graph = RealTimeGraph(monitoring_frame, "Error Rates")
        self.connection_graph = RealTimeGraph(monitoring_frame, "Active Connections")
        
        # Add server health indicators
        self.health_indicators = {
            'cpu_usage': tk.StringVar(),
            'memory_usage': tk.StringVar(),
            'network_throughput': tk.StringVar()
        }

def launch_gui():
    root = tk.Tk()
    app = LoadTesterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui() 