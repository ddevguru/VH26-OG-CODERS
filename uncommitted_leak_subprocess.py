"""UNCOMMITTED TEST FILE 4 — Unclosed Subprocess Pipe Resource Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_subprocess.py --voice
"""
import subprocess

def run_background_diagnostics(script_path: str):
    # Unclosed subprocess handle 'proc'
    with subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        stdout, stderr = proc.communicate()
        return proc.returncode
