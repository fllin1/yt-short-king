from ytsk.editing import CutsDetectorFactory, DownloaderFactory, extract_audio


def download_command(url: str, source: str = "youtube", verbose: bool = False):
    if source == "youtube":
        downloader = DownloaderFactory.create(source)
        downloader.download(url, verbose)
    else:
        raise ValueError(f"Invalid source: {source}")


def cuts_command(
    path: str,
    output: str | None = None,
    verbose: bool = False,
):
    """Detect scene cuts and split the video into clips."""
    detector = CutsDetectorFactory.create("scenedetect")
    output_dir = detector.detect_and_split(path, output_path=output, verbose=verbose)
    print(f"Saved {output_dir}")


def get_audio_command(
    path: str,
    output: str | None = None,
    format: str = "mp3",
    verbose: bool = False,
):
    """Extract audio from a video file."""
    out_path = extract_audio(path, output_path=output, format=format, verbose=verbose)
    print(f"Saved {out_path}")
