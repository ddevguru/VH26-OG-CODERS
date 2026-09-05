"use client";

import React, { useState, useEffect, useRef } from "react";
import { Volume2, VolumeX, Mic, MicOff, Settings, Sliders, Check, Sparkles, X, Activity } from "lucide-react";

interface VoiceAgentProps {
  autoAnnounceText?: string;
  onVoiceCommand?: (command: string) => void;
}

export const VoiceAgent: React.FC<VoiceAgentProps> = ({ autoAnnounceText, onVoiceCommand }) => {
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [showSettings, setShowSettings] = useState(false);

  // Settings State
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [rate, setRate] = useState<number>(1.0);
  const [pitch, setPitch] = useState<number>(1.0);
  const [chimeEnabled, setChimeEnabled] = useState<boolean>(true);

  const recognitionRef = useRef<any>(null);

  // Load available TTS voices
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    const updateVoices = () => {
      const available = window.speechSynthesis.getVoices();
      setVoices(available);
      if (available.length > 0 && !selectedVoice) {
        const englishVoice = available.find((v) => v.lang.startsWith("en")) || available[0];
        setSelectedVoice(englishVoice.name);
      }
    };

    updateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    const savedMute = localStorage.getItem("leakguard_voice_muted");
    if (savedMute === "true") setMuted(true);
  }, []);

  // Web Audio API Synth Chime
  const playChime = () => {
    if (!chimeEnabled || typeof window === "undefined") return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
      osc.frequency.exponentialRampToValueAtTime(783.99, ctx.currentTime + 0.15); // G5

      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (e) {}
  };

  // Text-To-Speech Output Engine
  const speak = (text: string) => {
    if (muted || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      playChime();

      setTimeout(() => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = rate;
        utterance.pitch = pitch;

        if (selectedVoice && voices.length > 0) {
          const matchedVoice = voices.find((v) => v.name === selectedVoice);
          if (matchedVoice) utterance.voice = matchedVoice;
        }

        utterance.onstart = () => setSpeaking(true);
        utterance.onend = () => setSpeaking(false);
        utterance.onerror = () => setSpeaking(false);
        window.speechSynthesis.speak(utterance);
      }, 150);
    } catch (e) {}
  };

  useEffect(() => {
    if (autoAnnounceText && !muted) {
      speak(autoAnnounceText);
    }
  }, [autoAnnounceText, muted]);

  // Speech-to-Text Voice Command Engine
  const toggleListening = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      speak("Browser speech recognition is not supported in this browser.");
      return;
    }

    if (listening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setListening(true);
        setTranscript("Listening for voice commands...");
      };

      recognition.onresult = (event: any) => {
        const current = event.resultIndex;
        const text = event.results[current][0].transcript.toLowerCase();
        setTranscript(text);

        if (event.results[current].isFinal) {
          processVoiceCommand(text);
        }
      };

      recognition.onerror = (e: any) => {
        setListening(false);
        setTranscript(`Voice error: ${e.error}`);
      };

      recognition.onend = () => {
        setListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e: any) {
      setListening(false);
      setTranscript("Microphone access denied.");
    }
  };

  const processVoiceCommand = (cmd: string) => {
    if (cmd.includes("mute")) {
      setMuted(true);
      speak("Voice alerts muted.");
      return;
    }
    if (cmd.includes("unmute") || cmd.includes("enable voice")) {
      setMuted(false);
      speak("Voice alerts unmuted.");
      return;
    }

    if (onVoiceCommand) {
      onVoiceCommand(cmd);
    }

    speak(`Recognized command: ${cmd}`);
  };

  const toggleMute = () => {
    const nextState = !muted;
    setMuted(nextState);
    if (typeof window !== "undefined") {
      localStorage.setItem("leakguard_voice_muted", String(nextState));
    }
    if (nextState) {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setSpeaking(false);
    } else {
      speak("Voice alerts activated.");
    }
  };

  return (
    <div className="relative inline-flex items-center gap-2">
      {/* Voice Toggle Button */}
      <button
        onClick={toggleMute}
        title={muted ? "Enable Voice Audio Alerts" : "Mute Voice Audio Alerts"}
        className={`px-3 py-1.5 rounded-xl border font-bold text-xs flex items-center gap-2 transition-all cursor-pointer ${
          muted
            ? "bg-slate-100 border-slate-300 text-slate-500 hover:bg-slate-200"
            : "bg-emerald-500/10 border-emerald-500/20 text-emerald-700 hover:bg-emerald-500/20 shadow-xs"
        }`}
      >
        {muted ? <VolumeX className="w-4 h-4 text-slate-400" /> : <Volume2 className="w-4 h-4 text-emerald-600 animate-pulse" />}
        <span>{muted ? "Voice Muted" : speaking ? "Speaking..." : "Voice Alerts Active"}</span>
      </button>

      {/* Microphone Input Button for Voice Commands */}
      <button
        onClick={toggleListening}
        title={listening ? "Stop Voice Listening" : "Speak Voice Command (Microphone)"}
        className={`p-1.5 rounded-xl border transition-all cursor-pointer flex items-center gap-1.5 ${
          listening
            ? "bg-red-500 text-white border-red-600 animate-pulse shadow-md shadow-red-500/30"
            : "bg-white border-slate-200 text-slate-700 hover:bg-slate-100"
        }`}
      >
        {listening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4 text-slate-500" />}
        {listening && <span className="text-[10px] font-bold pr-1">Listening</span>}
      </button>

      {/* Voice Settings Button */}
      <button
        onClick={() => setShowSettings(!showSettings)}
        title="Voice Customization Settings"
        className="p-1.5 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 transition cursor-pointer"
      >
        <Settings className="w-4 h-4" />
      </button>

      {/* Transcript Toast */}
      {transcript && (
        <div className="absolute top-10 left-0 z-40 bg-slate-900 text-emerald-400 px-3 py-1.5 rounded-xl text-[11px] font-mono-code shadow-xl border border-slate-700 whitespace-nowrap animate-in fade-in">
          🎙️ {transcript}
        </div>
      )}

      {/* Voice Customization Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-4 animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>Voice Agent Customization</span>
              </h3>
              <button onClick={() => setShowSettings(false)} className="p-1 text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">TTS Persona Voice</label>
                <select
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none"
                >
                  {voices.map((v, i) => (
                    <option key={i} value={v.name}>
                      {v.name} ({v.lang})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between font-bold text-[11px] text-slate-700 mb-1">
                  <span>Speech Speed (Rate)</span>
                  <span>{rate.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={rate}
                  onChange={(e) => setRate(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between font-bold text-[11px] text-slate-700 mb-1">
                  <span>Speech Pitch</span>
                  <span>{pitch.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="font-bold text-slate-700 text-xs">Audio Synth Chime Sound</span>
                <button
                  onClick={() => setChimeEnabled(!chimeEnabled)}
                  className={`px-3 py-1 rounded-xl font-bold text-[11px] border transition ${
                    chimeEnabled ? "bg-emerald-500 text-white border-emerald-600" : "bg-slate-100 text-slate-600 border-slate-200"
                  }`}
                >
                  {chimeEnabled ? "Chime ON" : "Chime OFF"}
                </button>
              </div>
            </div>

            <div className="pt-2 flex justify-between gap-2 border-t border-slate-200">
              <button
                onClick={() => speak("This is a test announcement of the LeakGuard Voice Agent persona.")}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs"
              >
                Test Voice
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
