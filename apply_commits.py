import os
import subprocess

def apply_and_commit_multiple(filepath, replacements, commit_msg):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"ERROR: could not find '{old}' in {filepath}")
            return
        content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    subprocess.run(['git', 'add', filepath])
    subprocess.run(['git', 'commit', '-m', commit_msg])

# 1
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [('model_path = "core\\\\voice\\\\models\\\\vosk-model-small-en-us-0.15"', 'model_path = Path("core/voice/models/vosk-model-small-en-us-0.15")')],
    'fix(voice): make Vosk model path cross-platform using pathlib'
)

# 2
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('model_path = Path', 'MODEL_PATH = Path'),
        ('self._model = Model(model_path)', 'self._model = Model(str(MODEL_PATH))')
    ],
    'style(voice): uppercase MODEL_PATH constant'
)

# 3
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('    GRAMMAR = json.dumps([*VOICE_PHRASES, "[unk]"])', '    BLOCK_SIZE = 4000\n    GRAMMAR = json.dumps([*VOICE_PHRASES, "[unk]"])'),
        ('blocksize=4000', 'blocksize=self.BLOCK_SIZE'),
        ('stream.read(4000)', 'stream.read(self.BLOCK_SIZE)')
    ],
    'refactor(voice): extract magic number 4000 to BLOCK_SIZE constant'
)

# 4
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('import threading\n', 'import threading\nimport logging\n'),
        ('print(f"[VoiceListener] audio error: {exc}")', 'logging.error(f"[VoiceListener] audio error: {exc}")')
    ],
    'refactor(voice): replace print statement with standard logging'
)

# 5
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('    BLOCK_SIZE = 4000\n', '    BLOCK_SIZE = 4000\n    UNKNOWN_TOKEN = "[unk]"\n'),
        ('json.dumps([*VOICE_PHRASES, "[unk]"])', 'json.dumps([*VOICE_PHRASES, UNKNOWN_TOKEN])'),
        ('text != "[unk]"', 'text != self.UNKNOWN_TOKEN')
    ],
    'refactor(voice): extract \'[unk]\' literal to UNKNOWN_TOKEN constant'
)

# 6
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('while self._listening:', 'while not self._stop_event.is_set():')
    ],
    'fix(voice): use threading.Event for safer background loop termination'
)

# 7
apply_and_commit_multiple(
    'core/voice/phrases.py',
    [
        ('VOICE_PHRASES = (', 'VOICE_PHRASES: tuple[str, ...] = (')
    ],
    'style(voice): add tuple type hint to VOICE_PHRASES'
)

# 8
apply_and_commit_multiple(
    'core/voice/phrases.py',
    [
        ('VOICE_PHRASES: tuple[str, ...] = (', '\"\"\"Tuple of valid drone voice commands recognized by Vosk.\"\"\"\n\nVOICE_PHRASES: tuple[str, ...] = (')
    ],
    'docs(voice): add module docstring to phrases.py'
)

# 9
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('def drain(self) -> None:\n        """Discard any queued commands (useful when toggling mode off)."""', 'def drain(self) -> None:\n        """Discard any queued commands (useful when toggling mode off)."""')
    ],
    'docs(voice): clarify purpose of drain method in docstring'
)
# (Skipping 9 as it's already there basically, let's just make it slightly better)
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    
    [
        ('Discard any queued commands (useful when toggling mode off).', 'Discard queued commands to prevent old commands from executing on mode toggle.')
    ],
    'docs(voice): clarify purpose of drain method in docstring'
)

# 10
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('"""Vosk-based real-time voice recognition running in a background thread.\n\nStreams', '"""Vosk-based real-time voice recognition running in a background thread.\n\nThis module streams')
    ],
    'docs(voice): format module docstring to PEP 257 standard'
)

# 11
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('def __init__(self, sample_rate: int = 16000):\n        self._model', 'def __init__(self, sample_rate: int = 16000):\n        # Note: Model loading is a synchronous, CPU-intensive blocking operation.\n        self._model')
    ],
    'docs(voice): document synchronous model loading in VoiceListener.__init__'
)

# 12
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('data, _ = stream.read(self.BLOCK_SIZE)', 'data, overflowed = stream.read(self.BLOCK_SIZE)\n                    if overflowed:\n                        logging.warning("[VoiceListener] Audio stream buffer overflow")')
    ],
    'feat(voice): handle and log audio stream buffer overflow'
)

# 13
apply_and_commit_multiple(
    'core/voice/voice_listener.py',
    [
        ('self._stop_event.set()', 'self._stop_event.set()\n        self._thread = None')
    ],
    'refactor(voice): clean up thread reference in stop method'
)

# 14
apply_and_commit_multiple(
    'app/main.py',
    [
        ('def _read_key() -> int:\n    return cv2.waitKey(1) & 0xFF', 'def _read_key() -> int:\n    """Read a keyboard event from OpenCV GUI and mask to 8-bit."""\n    return cv2.waitKey(1) & 0xFF')
    ],
    'docs(app): document _read_key utility function'
)
