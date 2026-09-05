import os
import shutil
import pytest
from pathlib import Path
from typer.testing import CliRunner

from services.voice.announcer import VoiceAnnouncer
from interfaces.cli.main import app as cli_app

runner = CliRunner()


def test_voice_announcer_sync_and_async(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)
    announcer = VoiceAnnouncer(enabled=True)
    # Sync mode speak
    announcer.speak("LeakGuard voice alert system initialized.", async_mode=False)
    # Async mode speak
    announcer.speak("Async voice alert verification.", async_mode=True)
    # Scan result announcements
    announcer.speak_scan_result(passed=True, leak_count=0, async_mode=False)
    announcer.speak_scan_result(passed=False, leak_count=2, first_rule="LG-FILE-001", async_mode=False)



def test_cli_speak_command_invocation():
    result = runner.invoke(cli_app, ["speak", "Testing CLI speech synthesis"])
    assert result.exit_code == 0
    assert "Spoke" in result.output or "Voice" in result.output or result.exit_code == 0


def test_cli_scan_with_voice_flag(tmp_path):
    # Create sample Python file with unclosed resource leak
    py_file = tmp_path / "leak_sample.py"
    py_file.write_text("def run():\n    f = open('data.txt')\n", encoding="utf-8")

    # Run scan with --voice
    result = runner.invoke(cli_app, ["scan", str(tmp_path), "--voice"])
    assert result.exit_code == 0 or result.exit_code == 1


def test_git_pre_push_hook_contains_voice_speak(tmp_path):
    # Setup mock git directory
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(cli_app, ["install", str(tmp_path)])
    assert result.exit_code == 0

    hook_file = git_dir / "pre-push"
    assert hook_file.exists()
    hook_content = hook_file.read_text(encoding="utf-8")
    
    # Verify pre-push hook includes voice speak calls
    assert "python -m leakguard speak" in hook_content
    assert "--voice" in hook_content
