from ytsk.videos.video_cuts_detect import CutsDetectorFactory
from ytsk.videos.video_download import DownloaderFactory


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
