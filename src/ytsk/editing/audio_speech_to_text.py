"""Transcribe audio to text using Whisper large-v3-turbo."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from ytsk.config import EXTERNAL_DIR


class Transcriber(ABC):
    @abstractmethod
    def transcribe(
        self,
        path_or_filename: str,
        output_path: str | None = None,
        language: str | None = None,
        task: str = "transcribe",
        return_timestamps: bool = False,
    ) -> tuple[str | dict, Path]:
        """Transcribe audio to text.

        Args:
            path_or_filename: Audio path or filename. If a full path is provided,
                it is used as-is. Otherwise resolved against EXTERNAL_DIR.
            output_path: If set, save to this path. If None, saves to
                {audio_folder}/transcript.json (or .txt when no metadata).
            language: Source language code (e.g. "en", "fr"). If None, auto-detect.
            task: "transcribe" (same language) or "translate" (to English).
            return_timestamps: If True, return dict with "text" and "chunks";
                otherwise return plain text string.

        Returns:
            Tuple of (transcribed text or dict with "text" and "chunks",
            path where transcript was saved).
        """
        pass


class WhisperTranscriberImpl(Transcriber):
    """Transcriber using Whisper large-v3-turbo."""

    MODEL_ID = "openai/whisper-large-v3-turbo"
    _pipeline = None

    def _get_pipeline(self):
        """Lazy-load the ASR pipeline to avoid loading the model on import."""
        if WhisperTranscriberImpl._pipeline is None:
            import torch
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
            from transformers.utils import logging as hf_logging

            # Suppress noisy logits-processor warnings (harmless, from pipeline internals)
            hf_logging.set_verbosity_error()

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.MODEL_ID,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )
            model.to(device)

            processor = AutoProcessor.from_pretrained(self.MODEL_ID)

            WhisperTranscriberImpl._pipeline = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                torch_dtype=torch_dtype,
                device=device,
            )
        return WhisperTranscriberImpl._pipeline

    def transcribe(
        self,
        path_or_filename: str,
        output_path: str | None = None,
        language: str | None = None,
        task: str = "transcribe",
        return_timestamps: bool = False,
    ) -> tuple[str | dict, Path]:
        p = Path(path_or_filename)
        if p.is_absolute() or len(p.parts) > 1:
            audio_path = p.resolve()
        else:
            audio_path = EXTERNAL_DIR / p

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        pipe = self._get_pipeline()

        generate_kwargs: dict = {"task": task}
        if language is not None:
            generate_kwargs["language"] = language

        # Long-form audio (>30s) requires return_timestamps=True; we extract text
        # when user did not request timestamps.
        result = pipe(
            str(audio_path),
            generate_kwargs=generate_kwargs,
            return_timestamps=True,
        )

        if return_timestamps:
            output = result
        else:
            output = result["text"] if isinstance(result, dict) else result

        # Default: save in same folder as audio, named "transcript"
        has_metadata = isinstance(result, dict) and "chunks" in result
        if output_path is None:
            ext = ".json" if has_metadata else ".txt"
            out = audio_path.parent / f"transcript{ext}"
        else:
            out = Path(output_path)
            if out.is_dir() or (not out.suffix and not out.exists()):
                ext = ".json" if has_metadata else ".txt"
                out = out / f"transcript{ext}"

        out.parent.mkdir(parents=True, exist_ok=True)
        # Use .json extension to decide: .json = full output, else = text only
        save_full = has_metadata and out.suffix.lower() == ".json"
        if save_full:
            with open(out, "w") as f:
                json.dump(result, f, indent=2)
        else:
            text = result["text"] if isinstance(result, dict) else result
            # Ensure .txt when saving text to a path without extension
            out = out if out.suffix else out.with_suffix(".txt")
            out.write_text(text, encoding="utf-8")

        return output, out


class TranscriberFactory:
    @staticmethod
    def create(strategy: str = "whisper") -> Transcriber:
        if strategy == "whisper":
            return WhisperTranscriberImpl()
        raise ValueError(f"Invalid strategy: {strategy}")


def transcribe(
    path_or_filename: str,
    output_path: str | None = None,
    language: str | None = None,
    task: str = "transcribe",
    return_timestamps: bool = False,
) -> tuple[str | dict, Path]:
    """Convenience function that delegates to TranscriberFactory."""
    return TranscriberFactory.create("whisper").transcribe(
        path_or_filename,
        output_path=output_path,
        language=language,
        task=task,
        return_timestamps=return_timestamps,
    )
