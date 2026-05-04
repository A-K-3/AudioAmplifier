from collections import deque

from amplifier.config import LOG_MAX_LINES

log_lines: deque[str] = deque(maxlen=LOG_MAX_LINES)


class LogTee:
    """File-like wrapper that mirrors writes to a real stream and to log_lines."""

    def __init__(self, real_stream):
        self.real = real_stream
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        try:
            self.real.write(s)
        except Exception:
            pass
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line:
                log_lines.append(line)
        return len(s)

    def flush(self):
        try:
            self.real.flush()
        except Exception:
            pass
