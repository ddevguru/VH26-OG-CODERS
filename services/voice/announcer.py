import sys
import os
import subprocess
import threading
from typing import Optional
from core.common.logger import get_logger

logger = get_logger("leakguard.voice")


class VoiceAnnouncer:
    """Voice Audio Announcer for LeakGuard CLI & Git Pre-push hooks.
    
    Uses Windows SAPI / PowerShell SpeechSynthesizer or pyttsx3 fallback.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def speak(self, text: str, async_mode: bool = True) -> None:
        if not self.enabled or not text:
            return

        def _do_speak():
            try:
                # Windows PowerShell Speech Synthesizer (Zero external dependencies required on Windows)
                if sys.platform == "win32":
                    clean_text = text.replace('"', '\\"').replace("'", "''")
                    ps_cmd = (
                        "Add-Type -AssemblyName System.Speech; "
                        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                        "$synth.SetOutputToDefaultAudioDevice(); "
                        f'$synth.Speak("{clean_text}");'
                    )


                    subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        timeout=10,
                    )
                    return
            except Exception as e:
                logger.debug(f"PowerShell SAPI TTS failed: {e}")

            # Try pyttsx3 fallback if installed
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.debug(f"pyttsx3 fallback failed: {e}")

        if async_mode:
            thread = threading.Thread(target=_do_speak, daemon=True)
            thread.start()
        else:
            _do_speak()

    def speak_scan_result(
        self,
        passed: bool,
        leak_count: int = 0,
        first_rule: Optional[str] = None,
        async_mode: bool = False,
    ) -> None:
        if passed or leak_count == 0:
            msg = "LeakGuard static check passed. Zero resource leaks detected."
        else:
            msg = f"Attention! LeakGuard detected {leak_count} unclosed resource leaks. Git push aborted."
            if first_rule:
                msg += f" Primary finding rule: {first_rule}."

        self.speak(msg, async_mode=async_mode)
