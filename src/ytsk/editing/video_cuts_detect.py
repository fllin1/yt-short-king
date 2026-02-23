import json
from abc import ABC, abstractmethod
from pathlib import Path

from scenedetect import (
    ContentDetector,
    SceneManager,
    open_video,
    split_video_ffmpeg,
)

from ytsk.config import EXTERNAL_DIR, RAW_DIR
from ytsk.utils import sanitize_title


class CutsDetector(ABC):
    @abstractmethod
    def detect_and_split(
        self,
        path_or_filename: str,
        output_path: str | None = None,
        verbose: bool = False,
    ) -> Path:
        """Detect scene cuts and split the video into scene clips.

        Args:
            path_or_filename: Video path or filename. If a full path is provided,
                it is used as-is. Otherwise resolved against EXTERNAL_DIR.
            output_path: Directory to save split clips. If None, uses
                RAW_DIR / video_title.
            verbose: If True, show progress and save cuts_timestamps.json.

        Returns:
            Path to the output directory containing split video clips.
        """
        pass


class SceneDetectStrategy(CutsDetector):
    """Scene detection using PySceneDetect ContentDetector and ffmpeg splitting."""

    def detect_and_split(
        self,
        path_or_filename: str,
        output_path: str | None = None,
        verbose: bool = False,
    ) -> Path:
        p = Path(path_or_filename)
        if p.is_absolute() or len(p.parts) > 1:
            video_path = p.resolve()
        else:
            video_path = EXTERNAL_DIR / p

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        video = open_video(str(video_path), backend="pyav")
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video=video, show_progress=verbose)
        scenes = scene_manager.get_scene_list(start_in_scene=True)

        video_title = video_path.stem
        safe_title = sanitize_title(video_title)
        output_dir = (
            Path(output_path).resolve()
            if output_path
            else RAW_DIR / safe_title / "scenes"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        def scene_formatter(video, scene):
            return f"scene_{scene.index + 1}.mp4"

        split_video_ffmpeg(
            str(video_path),
            scenes,
            output_dir=output_dir,
            formatter=scene_formatter,
            video_name=safe_title,
            show_progress=verbose,
        )

        if verbose:
            cuts_data = [
                {
                    "scene": i + 1,
                    "start_seconds": round(start.get_seconds(), 2),
                    "start_frame": start.get_frames(),
                    "end_seconds": round(end.get_seconds(), 2),
                    "end_frame": end.get_frames(),
                }
                for i, (start, end) in enumerate(scenes)
            ]
            cuts_path = output_dir / "cuts_timestamps.json"
            with open(cuts_path, "w") as f:
                json.dump(cuts_data, f, indent=2)

        return output_dir


class CutsDetectorFactory:
    @staticmethod
    def create(strategy: str = "scenedetect") -> CutsDetector:
        if strategy == "scenedetect":
            return SceneDetectStrategy()
        raise ValueError(f"Invalid strategy: {strategy}")
