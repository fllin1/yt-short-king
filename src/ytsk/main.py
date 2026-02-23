"""yt-short-king CLI: video and audio processing for YouTube shorts.

Command hierarchy:
  ytsk video <subcommand>   - Video operations: download, cuts, extract audio
  ytsk audio <subcommand>   - Audio operations: transcribe

Usage examples:
  ytsk video download https://youtube.com/watch?v=...
  ytsk video cuts my_video.mp4 -o data/raw/my_video
  ytsk video get-audio my_video.mp4 -f mp3 -o data/raw/my_video/audio.mp3
  ytsk audio transcribe audio.mp3 -o transcript.txt
  ytsk audio transcribe audio.mp3 -l fr -t translate --timestamps

Help:
  ytsk --help              - List top-level commands
  ytsk video --help        - List video subcommands
  ytsk audio --help        - List audio subcommands
"""

import typer

from ytsk.cli.cli_audios import transcribe_command
from ytsk.cli.cli_videos import cuts_command, download_command, get_audio_command

app = typer.Typer(no_args_is_help=True)

video_app = typer.Typer(help="Video operations: download, cuts, extract audio")
audio_app = typer.Typer(help="Audio operations: transcribe")

app.add_typer(video_app, name="video")
app.add_typer(audio_app, name="audio")


@video_app.command(help="Download a video from YouTube or other sources")
def download(url: str, source: str = "youtube", verbose: bool = False):
    download_command(url, source, verbose)


@video_app.command(help="Detect scene cuts and split the video into scene clips")
def cuts(
    path: str = typer.Argument(..., help="Video path or filename"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output directory for split clips"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show progress and save cuts_timestamps.json",
    ),
):
    cuts_command(path, output=output, verbose=verbose)


@video_app.command(help="Extract audio from a video file")
def get_audio(
    path: str = typer.Argument(..., help="Video path or filename"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file or directory"
    ),
    format: str = typer.Option(
        "mp3",
        "--format",
        "-f",
        help="Output format: mp3 or m4a",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show ffmpeg output",
    ),
):
    get_audio_command(path, output=output, format=format, verbose=verbose)


@audio_app.command(help="Transcribe audio to text using Whisper large-v3-turbo")
def transcribe(
    path: str = typer.Argument(..., help="Audio path or filename"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file for transcript"
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Source language code (e.g. en, fr). Auto-detect if not set",
    ),
    task: str = typer.Option(
        "transcribe",
        "--task",
        "-t",
        help="transcribe (same language) or translate (to English)",
    ),
    timestamps: bool = typer.Option(
        False,
        "--timestamps",
        help="Return sentence-level timestamps",
    ),
):
    transcribe_command(
        path,
        output=output,
        language=language,
        task=task,
        timestamps=timestamps,
    )


if __name__ == "__main__":
    app()
