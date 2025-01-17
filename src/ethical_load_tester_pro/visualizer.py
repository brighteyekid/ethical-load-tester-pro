import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from queue import Queue
import threading

class ResultVisualizer:
    def __init__(self, output_dir: str = "reports"):
        # Create reports directory if it doesn't exist
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a default style instead of seaborn
        plt.style.use('default')
        
        # Define colors for plots
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        # Initialize plot queue
        self.plot_queue = Queue()
        
        # Add cleanup of old reports
        self.max_reports = 10
        self._cleanup_old_reports()

    def _cleanup_old_reports(self):
        """Cleanup old report files to prevent disk space issues"""
        try:
            reports = sorted(self.output_dir.glob('*.png'), 
                            key=lambda x: x.stat().st_mtime)
            while len(reports) > self.max_reports:
                reports[0].unlink()
                reports.pop(0)
        except Exception as e:
            print(f"Warning: Could not cleanup old reports: {str(e)}")

    def _create_response_time_plot(self, response_times: List[float], test_duration: float) -> str:
        """Create response time distribution plot"""
        try:
            plt.figure(figsize=(12, 8))
            
            # Create subplot grid
            gs = plt.GridSpec(2, 2)
            
            # Response time histogram
            ax1 = plt.subplot(gs[0, :])
            # Use plain matplotlib histogram instead of seaborn
            ax1.hist(response_times, bins=30, color=self.colors[0], alpha=0.7)
            ax1.set_title('Response Time Distribution')
            ax1.set_xlabel('Response Time (seconds)')
            ax1.set_ylabel('Frequency')
            
            # Add statistical annotations
            stats_text = f'Min: {min(response_times):.3f}s\n'
            stats_text += f'Max: {max(response_times):.3f}s\n'
            stats_text += f'Avg: {sum(response_times)/len(response_times):.3f}s'
            
            ax1.text(0.95, 0.95, stats_text,
                     transform=ax1.transAxes,
                     verticalalignment='top',
                     horizontalalignment='right',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            output_file = self.output_dir / 'response_time_analysis.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(output_file)
        except Exception as e:
            print(f"Error creating response time plot: {str(e)}")
            return None

    def _create_status_code_plot(self, status_codes: Dict[int, int]) -> str:
        """Create a pie chart of status code distribution."""
        plt.figure(figsize=(10, 8))
        
        labels = [f"Status {code}" for code in status_codes.keys()]
        sizes = list(status_codes.values())
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title('Status Code Distribution')
        
        output_file = self.output_dir / 'status_code_distribution.png'
        plt.savefig(output_file)
        plt.close()
        
        return str(output_file)

    def _create_requests_timeline(self, timestamps: List[float], 
                               response_times: List[float]) -> str:
        """Create a timeline of requests showing response times."""
        plt.figure(figsize=(12, 6))
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'response_time': response_times
        })
        
        df['rolling_avg'] = df['response_time'].rolling(window=20).mean()
        
        plt.scatter(df['timestamp'], df['response_time'], 
                   alpha=0.3, label='Individual Requests')
        plt.plot(df['timestamp'], df['rolling_avg'], 
                color='red', label='Rolling Average')
        
        plt.title('Request Response Times Over Test Duration')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Response Time (seconds)')
        plt.legend()
        
        output_file = self.output_dir / 'request_timeline.png'
        plt.savefig(output_file)
        plt.close()
        
        return str(output_file)

    def create_response_time_plot(self, *args, **kwargs) -> str:
        """Queue the response time plot creation."""
        self.plot_queue.put(('response_time', args, kwargs))
        return str(self.output_dir / 'response_time_distribution.png')

    def create_status_code_plot(self, *args, **kwargs) -> str:
        """Queue the status code plot creation."""
        self.plot_queue.put(('status_code', args, kwargs))
        return str(self.output_dir / 'status_code_distribution.png')

    def create_requests_timeline(self, *args, **kwargs) -> str:
        """Queue the requests timeline plot creation."""
        self.plot_queue.put(('timeline', args, kwargs))
        return str(self.output_dir / 'request_timeline.png')

    def process_plots(self):
        """Process all queued plots in the main thread."""
        while not self.plot_queue.empty():
            plot_type, args, kwargs = self.plot_queue.get()
            try:
                if plot_type == 'response_time':
                    self._create_response_time_plot(*args, **kwargs)
                elif plot_type == 'status_code':
                    self._create_status_code_plot(*args, **kwargs)
                elif plot_type == 'timeline':
                    self._create_requests_timeline(*args, **kwargs)
            except Exception as e:
                print(f"Error creating {plot_type} plot: {str(e)}")
            finally:
                self.plot_queue.task_done() 