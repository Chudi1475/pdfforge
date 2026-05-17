"""Text-to-speech read-aloud using pyttsx3 (offline)."""
from __future__ import annotations
from typing import Optional, Callable
from PySide6.QtCore import QObject, QThread, Signal


class _SpeakThread(QThread):
    finished_speaking = Signal()
    failed = Signal(str)
    progress = Signal(int)  # page index being spoken

    def __init__(self, pages_text: list[tuple[int, str]],
                 rate: int = 180, voice_id: Optional[str] = None):
        super().__init__()
        self.pages_text = pages_text
        self.rate = rate
        self.voice_id = voice_id
        self._stop = False

    def request_stop(self):
        self._stop = True
        try:
            import pyttsx3
            # there's no clean way to break the engine mid-utterance,
            # but stopping the engine after current chunk works
        except Exception:
            pass

    def run(self):
        try:
            import pyttsx3
        except Exception as e:
            self.failed.emit(f"pyttsx3 not available: {e}")
            return
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            if self.voice_id:
                engine.setProperty("voice", self.voice_id)
            for page_idx, text in self.pages_text:
                if self._stop:
                    break
                self.progress.emit(page_idx)
                # speak in shorter chunks so stop is more responsive
                chunks = [s for s in text.split(". ") if s.strip()]
                for c in chunks:
                    if self._stop: break
                    engine.say(c)
                    engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
            self.finished_speaking.emit()
        except Exception as e:
            self.failed.emit(str(e))


class TtsReader(QObject):
    speaking_page = Signal(int)
    stopped = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: Optional[_SpeakThread] = None

    @staticmethod
    def list_voices() -> list[tuple[str, str]]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            return [(v.id, getattr(v, "name", v.id)) for v in voices]
        except Exception:
            return []

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self, pages_text: list[tuple[int, str]],
              rate: int = 180, voice_id: Optional[str] = None):
        self.stop()
        self._thread = _SpeakThread(pages_text, rate=rate, voice_id=voice_id)
        self._thread.progress.connect(self.speaking_page.emit)
        self._thread.finished_speaking.connect(self._on_done)
        self._thread.failed.connect(self.failed.emit)
        self._thread.start()

    def stop(self):
        if self._thread and self._thread.isRunning():
            self._thread.request_stop()
            self._thread.wait(1500)
        self._thread = None
        self.stopped.emit()

    def _on_done(self):
        self._thread = None
        self.stopped.emit()
