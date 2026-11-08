"""WAV inspection and normalisation (no ffmpeg needed: the browser sends 16 kHz mono PCM WAV)."""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass


class AudioError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class WavInfo:
    sample_rate: int
    channels: int
    sample_width: int
    data_offset: int
    data_len: int

    @property
    def duration_s(self) -> float:
        frame = self.channels * self.sample_width
        return self.data_len / (self.sample_rate * frame) if frame and self.sample_rate else 0.0


def parse_wav(buf: bytes) -> WavInfo:
    """Parse a RIFF/WAVE PCM file. Tolerates the placeholder sizes some streaming encoders write."""
    if len(buf) < 44 or buf[:4] != b"RIFF" or buf[8:12] != b"WAVE":
        raise AudioError("UNSUPPORTED_AUDIO_FORMAT", "Audio must be a WAV (RIFF/WAVE) file.")
    pos = 12
    fmt: tuple[int, int, int] | None = None
    while pos + 8 <= len(buf):
        cid = buf[pos:pos + 4]
        size = struct.unpack("<I", buf[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            audio_format, channels, rate = struct.unpack("<HHI", buf[body:body + 8])
            bits = struct.unpack("<H", buf[body + 14:body + 16])[0]
            if audio_format not in (1, 0xFFFE):
                raise AudioError("UNSUPPORTED_AUDIO_FORMAT", "Only PCM WAV audio is supported.")
            fmt = (rate, channels, bits // 8)
        elif cid == b"data":
            if fmt is None:
                raise AudioError("UNSUPPORTED_AUDIO_FORMAT", "WAV data chunk before fmt chunk.")
            actual = len(buf) - body
            data_len = min(size, actual)  # placeholder sizes (0xFFFFFFFF etc.) are clamped
            return WavInfo(fmt[0], fmt[1], fmt[2], body, data_len)
        pos = body + size + (size & 1)
    raise AudioError("UNSUPPORTED_AUDIO_FORMAT", "WAV file has no audio data.")


def normalise_wav(buf: bytes) -> bytes:
    """Rewrite as a canonical 44-byte-header WAV with correct sizes."""
    info = parse_wav(buf)
    data = buf[info.data_offset:info.data_offset + info.data_len]
    return build_wav(data, info.sample_rate, info.channels, info.sample_width)


def build_wav(pcm: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
    out = io.BytesIO()
    byte_rate = sample_rate * channels * sample_width
    out.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
    out.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate,
                                    channels * sample_width, sample_width * 8))
    out.write(b"data" + struct.pack("<I", len(pcm)) + pcm)
    return out.getvalue()


def rms_level(buf: bytes) -> float:
    """Root-mean-square level (0..1) of 16-bit PCM, used to reject silent recordings."""
    info = parse_wav(buf)
    if info.sample_width != 2:
        return 1.0
    data = buf[info.data_offset:info.data_offset + info.data_len]
    n = len(data) // 2
    if n == 0:
        return 0.0
    step = max(1, n // 20000)
    samples = struct.unpack(f"<{n}h", data[: n * 2])[::step]
    return (sum(s * s for s in samples) / len(samples)) ** 0.5 / 32768.0


MIN_SECONDS = 0.3
MAX_SECONDS = 30.0  # Prisma REST limit per docs.gnani.ai (verified page: "Maximum duration: 30 seconds")
SILENCE_RMS = 0.003


def validate_for_stt(buf: bytes) -> WavInfo:
    info = parse_wav(buf)
    if info.data_len == 0:
        raise AudioError("EMPTY_AUDIO", "The recording is empty.")
    if info.duration_s < MIN_SECONDS:
        raise AudioError("TOO_SHORT", "The recording is too short. Hold the button and speak a full sentence.")
    if info.duration_s > MAX_SECONDS:
        raise AudioError("TOO_LONG", f"The recording is longer than {int(MAX_SECONDS)} seconds.")
    if rms_level(buf) < SILENCE_RMS:
        raise AudioError("SILENCE", "We could not hear any speech. Please speak closer to the microphone.")
    return info
