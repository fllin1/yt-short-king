import typer

from ytsk.cli.cli_videos import cuts_command, download_command

app = typer.Typer(no_args_is_help=True)


@app.command(help="Download a video from YouTube or other sources")
def download(url: str, source: str = "youtube", verbose: bool = False):
    download_command(url, source, verbose)


@app.command(help="Detect scene cuts and split the video into scene clips")
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


if __name__ == "__main__":
    app()
