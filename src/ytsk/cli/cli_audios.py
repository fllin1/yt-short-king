from ytsk.editing import TranscriberFactory


def transcribe_command(
    path: str,
    output: str | None = None,
    language: str | None = None,
    task: str = "transcribe",
    timestamps: bool = False,
):
    """Transcribe audio to text using Whisper large-v3-turbo."""
    transcriber = TranscriberFactory.create("whisper")
    result, saved_path = transcriber.transcribe(
        path,
        output_path=output,
        language=language,
        task=task,
        return_timestamps=timestamps,
    )
    if isinstance(result, str):
        print(result)
    else:
        print(result.get("text", ""))
    print(f"Saved to {saved_path}")
