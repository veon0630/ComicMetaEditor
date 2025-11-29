# Performance Monitoring Utilities
"""
Performance monitoring and profiling utilities for ComicMeta Editor.
"""

import time
import functools
from utils.logger import logger


def timing_decorator(func):
    """
    Decorator to measure and log function execution time.
    Only logs if execution takes longer than 100ms.
    
    Usage:
        @timing_decorator
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        
        if elapsed > 0.1:  # Only log slow operations (>100ms)
            logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        
        return result
    return wrapper


class PerformanceMonitor:
    """
    Context manager for monitoring performance of code blocks.
    
    Usage:
        with PerformanceMonitor("Loading files"):
            # ... code to monitor
            pass
    """
    
    def __init__(self, operation_name, log_threshold=0.1):
        """
        Args:
            operation_name: Name of the operation being monitored
            log_threshold: Minimum time (seconds) to trigger logging
        """
        self.operation_name = operation_name
        self.log_threshold = log_threshold
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        
        if elapsed > self.log_threshold:
            logger.debug(f"{self.operation_name} completed in {elapsed:.3f}s")
        
        return False  # Don't suppress exceptions


class MemoryMonitor:
    """
    Monitor memory usage of the application.
    Requires psutil to be installed.
    """
    
    @staticmethod
    def get_current_memory_mb():
        """Get current process memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            logger.warning("psutil not installed, memory monitoring unavailable")
            return 0
    
    @staticmethod
    def log_memory_usage(label=""):
        """Log current memory usage with optional label"""
        memory_mb = MemoryMonitor.get_current_memory_mb()
        if memory_mb > 0:
            logger.debug(f"Memory usage{' (' + label + ')' if label else ''}: {memory_mb:.1f} MB")


# Example usage in code:
# 
# from utils.profiler import timing_decorator, PerformanceMonitor, MemoryMonitor
# 
# @timing_decorator
# def load_large_file(path):
#     with PerformanceMonitor("Reading zip"):
#         # ... read zip file
#         pass
#     MemoryMonitor.log_memory_usage("After loading")
