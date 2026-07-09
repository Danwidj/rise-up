"""Local video handling: validation and encoding. No network calls.

Everything here concerns the *local* mp4 file:
  - `probe_video`      : read metadata with ffprobe
  - `check_constraints`: verify it meets the model's limits (mp4, <= 2 minutes)
  - `print_report`     : show a human-readable summary
  - `to_data_url`      : encode it as the base64 data URL the API expects

The model's documented video limits (from the model card):
    Video: mp4, up to 2 minutes.
      - 1080p or higher     -> sample up to 1 FPS / 128 frames
      - lower res (e.g 720p) -> sample up to 2 FPS / 256 frames
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

MAX_DURATION_S = 120.0            # up to 2 minutes
CONTENT_TYPE = "video/mp4"
# Videos are inlined as base64 (the hosted model accepts only base64 data URLs,
# not NVCF asset-id references). base64 adds ~33%, so warn above this raw size.
LARGE_INLINE_WARN_BYTES = 30 * 1024 * 1024


class ValidationError(Exception):
    """Raised when the video cannot be read or fails a requirement."""


@dataclass
class VideoInfo:
    """Metadata about a local video file, as read by ffprobe."""

    path: str
    size_bytes: int
    duration_s: float
    width: int
    height: int
    fps: float
    codec: str
    container: str

    @property
    def is_1080p_or_higher(self) -> bool:
        # Tier by the short side: >= 1080 covers 1080p/1440p/4K and tall portrait.
        return min(self.width, self.height) >= 1080

    def sampling(self) -> tuple[int, int]:
        """Recommended (fps, num_frames) for this resolution, per the model card."""
        if self.is_1080p_or_higher:
            return 1, 128          # 1080p+: up to 1 FPS / 128 frames
        return 2, 256              # 720p and lower: up to 2 FPS / 256 frames


def probe_video(path: str) -> VideoInfo:
    """Read container/stream metadata with ffprobe. Raises ValidationError on failure."""
    if shutil.which("ffprobe") is None:
        raise ValidationError(
            "ffprobe not found on PATH. Install ffmpeg "
            "(macOS: `brew install ffmpeg`, Ubuntu: `apt install ffmpeg`)."
        )
    if not os.path.isfile(path):
        raise ValidationError(f"Video file not found: {path}")

    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ValidationError(f"ffprobe could not read {path!r}:\n{proc.stderr.strip()}")

    meta = json.loads(proc.stdout)
    fmt = meta.get("format", {})
    video_stream = next(
        (s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if video_stream is None:
        raise ValidationError("No video stream found in the file.")

    duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)
    fps = _parse_fps(video_stream.get("avg_frame_rate", "0/0")) or _parse_fps(
        video_stream.get("r_frame_rate", "0/0")
    )
    return VideoInfo(
        path=path,
        size_bytes=int(fmt.get("size") or os.path.getsize(path)),
        duration_s=duration,
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        fps=fps,
        codec=video_stream.get("codec_name", "unknown"),
        container=fmt.get("format_name", "unknown"),
    )


def check_constraints(info: VideoInfo) -> list[str]:
    """Return a list of problems. An empty list means the video is valid."""
    problems: list[str] = []

    ext = os.path.splitext(info.path)[1].lower()
    if ext != ".mp4":
        problems.append(f"file extension must be .mp4 (got '{ext or 'none'}').")

    # mp4 files are reported by ffprobe under the shared MOV/MP4 demuxer family.
    if "mp4" not in info.container.lower():
        problems.append(f"container '{info.container}' is not an MP4 container.")

    if info.duration_s <= 0:
        problems.append("could not determine a valid duration.")
    elif info.duration_s > MAX_DURATION_S:
        problems.append(
            f"duration {info.duration_s:.1f}s exceeds the "
            f"{MAX_DURATION_S:.0f}s (2 minute) limit."
        )

    if info.width <= 0 or info.height <= 0:
        problems.append("could not determine video resolution.")

    return problems


def print_report(info: VideoInfo) -> None:
    """Print a human-readable validation report."""
    fps, num_frames = info.sampling()
    tier = "1080p or higher" if info.is_1080p_or_higher else "720p or lower"
    est = min(num_frames, int(info.duration_s * fps)) if info.duration_s else num_frames
    print("Video validation")
    print("-" * 60)
    print(f"  file       : {info.path}")
    print(f"  size       : {info.size_bytes / 1_048_576:.2f} MiB")
    print(f"  container  : {info.container}")
    print(f"  codec      : {info.codec}")
    print(f"  resolution : {info.width}x{info.height} ({tier})")
    print(f"  duration   : {info.duration_s:.1f}s (limit {MAX_DURATION_S:.0f}s)")
    print(f"  source fps : {info.fps:.3f}")
    print(f"  sampling   : up to {fps} FPS / {num_frames} frames (~{est} for this clip)")
    print("-" * 60)


def to_data_url(path: str) -> str:
    """Read the video and return it as a base64 `data:` URL for the API."""
    size = os.path.getsize(path)
    if size > LARGE_INLINE_WARN_BYTES:
        print(
            f"warning: {size / 1_048_576:.1f} MiB video is inlined as base64 "
            f"(~{size * 4 / 3 / 1_048_576:.1f} MiB in the request); very large "
            "files may be rejected by the endpoint.",
            file=sys.stderr,
        )
    print(f"Encoding {size / 1_048_576:.2f} MiB video as base64 ...")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{CONTENT_TYPE};base64,{b64}"


def compress_video(input_path: str, output_path: str, duration_s: float, target_size_bytes: int = 19000000) -> None:
    """Compress the video using ffmpeg to fit under the target size (default ~18.1MB / 19,000,000 bytes)."""
    if shutil.which("ffmpeg") is None:
        raise ValidationError(
            "ffmpeg not found on PATH. Install ffmpeg to enable automatic video compression "
            "(macOS: `brew install ffmpeg`, Ubuntu: `apt install ffmpeg`)."
        )
    print(f"Compressing video to target size < {target_size_bytes / 1_048_576:.2f} MiB using ffmpeg...")
    
    # Calculate target bitrate
    target_bits = target_size_bytes * 8
    total_bitrate = int(target_bits / duration_s)
    audio_bitrate = 96000  # 96k for audio
    video_bitrate = max(100000, total_bitrate - audio_bitrate)
    
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", input_path,
         "-vcodec", "libx264", "-b:v", str(video_bitrate),
         "-acodec", "aac", "-b:a", str(audio_bitrate),
         "-preset", "fast", output_path],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise ValidationError(f"ffmpeg compression failed:\n{proc.stderr.strip()}")



def _parse_fps(rate: str) -> float:
    """ffprobe frame rates look like '30/1' or '30000/1001'."""
    if not rate or rate == "0/0":
        return 0.0
    if "/" in rate:
        num, den = rate.split("/", 1)
        return float(num) / float(den) if float(den) else 0.0
    return float(rate)
