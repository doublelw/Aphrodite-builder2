"""
Pipeline monitoring dashboard.

Real-time status of computational jobs, cluster nodes,
and screening progress. Terminal-based display.
"""
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class JobStatus:
    name: str
    status: str  # pending/running/completed/failed
    tier: str  # xtb/dft/dlpno
    progress: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    node: str = "unknown"
    error: Optional[str] = None


@dataclass
class NodeStatus:
    name: str
    address: str
    online: bool = False
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_jobs: int = 0
    total_jobs: int = 0


class PipelineMonitor:
    """
    Monitor computational pipeline status.

    Scans workdir for job status files and ORCA output progress.
    Tracks cluster node health via SSH ping.
    """

    def __init__(self, workdir: str = '.'):
        self.workdir = Path(workdir)

    def scan_jobs(self) -> List[JobStatus]:
        """Scan workdir for active and completed jobs."""
        jobs = []

        # Check for ORCA output files
        for out_file in self.workdir.rglob('*.out'):
            name = out_file.stem
            parent = out_file.parent.name

            # Determine tier from path
            tier = 'unknown'
            for t in ['xtb', 'dft', 'dlpno']:
                if t in str(out_file):
                    tier = t
                    break

            # Check completion
            content = ''
            if out_file.exists() and out_file.stat().st_size > 0:
                try:
                    content = out_file.read_text(errors='ignore')
                except:
                    pass

            if 'ORCA TERMINATED NORMALLY' in content:
                status = 'completed'
                progress = 1.0
            elif content and 'aborting' in content.lower():
                status = 'failed'
                progress = 0.0
            elif content:
                # Estimate progress from SCF cycles
                scf_lines = [l for l in content.split('\n') if 'SCF CONVERGED' in l]
                progress = min(len(scf_lines) / 3.0, 0.95) if scf_lines else 0.1
                status = 'running'
            else:
                status = 'pending'
                progress = 0.0

            jobs.append(JobStatus(
                name=name, status=status, tier=tier, progress=progress,
                node=parent,
            ))

        return jobs

    def get_summary(self) -> Dict[str, int]:
        """Get job summary counts."""
        jobs = self.scan_jobs()
        return {
            'total': len(jobs),
            'completed': sum(1 for j in jobs if j.status == 'completed'),
            'running': sum(1 for j in jobs if j.status == 'running'),
            'pending': sum(1 for j in jobs if j.status == 'pending'),
            'failed': sum(1 for j in jobs if j.status == 'failed'),
        }


def print_dashboard(workdir: str = '.'):
    """Print terminal monitoring dashboard."""
    monitor = PipelineMonitor(workdir)
    summary = monitor.get_summary()
    jobs = monitor.scan_jobs()

    width = 60
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n{'=' * width}")
    print(f"  BatteryFold Pipeline Monitor    {now}")
    print(f"{'=' * width}")

    # Summary bar
    total = max(summary['total'], 1)
    completed_pct = summary['completed'] / total * 100
    bar_len = width - 20
    filled = int(completed_pct / 100 * bar_len)
    bar = '#' * filled + '-' * (bar_len - filled)
    print(f"\n  Progress: [{bar}] {completed_pct:.0f}%")
    print(f"  Total: {summary['total']}  Done: {summary['completed']}  "
          f"Running: {summary['running']}  Failed: {summary['failed']}")

    # Job details
    if jobs:
        print(f"\n  {'Name':<25} {'Tier':<8} {'Status':<12} {'Progress'}")
        print(f"  {'-' * 56}")
        for job in sorted(jobs, key=lambda j: (j.status, j.name)):
            status_marker = {
                'completed': '+', 'running': '>', 'failed': 'x', 'pending': '.'
            }.get(job.status, '?')
            print(f"  [{status_marker}] {job.name:<23} {job.tier:<8} "
                  f"{job.status:<12} {job.progress:.0%}")

    print(f"\n{'=' * width}\n")


def watch_dashboard(workdir: str = '.', interval: int = 10):
    """Live monitoring mode — refreshes every N seconds."""
    try:
        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            print_dashboard(workdir)
            print(f"  Refreshing every {interval}s. Ctrl+C to stop.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
