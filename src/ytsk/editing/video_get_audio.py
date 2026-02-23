"""Extract audio from downloaded videos using ffmpeg."""

import subprocess
from pathlib import Path

from ytsk.config import EXTERNAL_DIR, RAW_DIR


def extract_audio(
    path_or_filename: str,
    output_path: str | None = None,
    format: str = "mp3",
    verbose: bool = False,
) -> Path:
    """Extract audio from a video file.

    Args:
        path_or_filename: Video path or filename. If a full path is provided,
            it is used as-is. Otherwise resolved against EXTERNAL_DIR.
        output_path: Output file or directory. If None, uses same directory as
            input with stem + extension. If a directory, appends stem + extension.
        format: Output format: "mp3" (default) or "m4a".
        verbose: If True, show ffmpeg output.

    Returns:
        Path to the extracted audio file.

    Raises:
        ValueError: If format is not "mp3" or "m4a".
        FileNotFoundError: If the video file does not exist.
        subprocess.CalledProcessError: If ffmpeg fails (e.g. no audio stream).
    """
    if format not in ("mp3", "m4a"):
        raise ValueError(f"Format must be 'mp3' or 'm4a', got {format!r}")
    p = Path(path_or_filename)
    if p.is_absolute() or len(p.parts) > 1:
        video_path = p.resolve()
    else:
        video_path = EXTERNAL_DIR / p

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    ext = "mp3" if format == "mp3" else "m4a"
    if output_path is None:
        out_path = RAW_DIR / video_path.stem / f"audio.{ext}"
    else:
        out = Path(output_path).resolve()
        if out.is_dir() or (not out.suffix and not out.exists()):
            out_path = out / f"{video_path.stem}.{ext}"
        else:
            out_path = out if out.suffix else out.with_suffix(f".{ext}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "mp3":
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            "-y",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=not verbose)
    else:
        # M4A: try copy first, fallback to aac encode
        cmd_copy = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "copy",
            "-y",
            str(out_path),
        ]
        result = subprocess.run(cmd_copy, capture_output=True, text=True)
        if result.returncode != 0:
            cmd_aac = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vn",
                "-acodec",
                "aac",
                "-y",
                str(out_path),
            ]
            subprocess.run(cmd_aac, check=True, capture_output=not verbose)
        elif verbose:
            print(result.stderr or result.stdout or "")

    return out_path
