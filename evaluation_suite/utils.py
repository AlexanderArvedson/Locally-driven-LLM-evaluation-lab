"""
Utility functions for evaluation runners.
"""

import uuid
import json
import platform
import psutil
import sys
from datetime import datetime


def generate_run_id():
    """Generate a unique UUID for this run."""
    return str(uuid.uuid4())


def get_system_info():
    """Collect system metadata for the run."""
    try:
        # Get CPU info
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": platform.system(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "cpu": {
                "physical_cores": cpu_count,
                "logical_cores": cpu_count_logical,
                "frequency_mhz": cpu_freq.current if cpu_freq else None
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": f"Failed to collect system info: {str(e)}",
            "system": platform.system(),
            "python_version": platform.python_version()
        }


def save_run_results(run_id, results_data, output_file):
    """Save run results with metadata to a JSON file."""
    output = {
        "run_id": run_id,
        "metadata": get_system_info(),
        "results": results_data
    }
    
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
