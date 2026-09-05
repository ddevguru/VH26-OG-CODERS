"""UNCOMMITTED TEST FILE 4 — Unterminated Subprocess Handle Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_subprocess.py --voice
"""
import subprocess

def spawn_background_task(cmd: list):
    # Unterminated subprocess handle 'proc'
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.pid
