"""TEST FILE 4 — Unclosed Subprocess Pipe Leak
Test CLI scan: python -m leakguard scan uncommitted_test_subprocess_leak.py --voice
Test CLI fix:  python -m leakguard fix uncommitted_test_subprocess_leak.py
"""
import subprocess

def execute_system_check(cmd_args: list):
    # Unclosed subprocess handle 'sub_proc'
    with subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as sub_proc:
        stdout, stderr = sub_proc.communicate()
        return sub_proc.returncode == 0
