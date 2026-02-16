# Changelog

## 2026-02-16

- Implemented `video_cuts_detect` module with scenedetect strategy
- Added RAW_DIR to config
- Scene detection via ContentDetector, splitting via split_video_ffmpeg
- Optional cuts_timestamps.json export when verbose
- `detect_and_split` accepts full path or filename; optional `output_path` for custom save location
- Added `cuts` CLI command in main.py with `path`, `-o/--output`, `-v/--verbose` options
- Typer app uses `no_args_is_help=True` so running `ytsk` without a command shows help
- Switched scene detection to PyAV backend to fix AV1 decoding errors (OpenCV lacks AV1 support on some platforms)
- Video download: sanitize title (spaces→underscores, remove special chars) via `sanitize_title()` in utils
- Cuts: output dir and filenames use sanitized title to avoid path/encoding issues; scenes named `scene_1.mp4`, `scene_2.mp4`, etc.

## 2026-02-13

- Added new Modal endpoints in `modal/image_generator.py`:
  - `generate_video` for Veo scene clip generation (5s, 9:16 default) using `GEMINI_API_KEY`.
  - `translate_french` for French translation of scene narration text.
  - `generate_french_voice` for ElevenLabs French TTS output (`audio/mpeg`).
- Kept existing bearer-token protection pattern for all new endpoints and reused existing Modal secret strategy.
- Extended `n8n/stealing-bones.json` with new scene-level pipeline after `Add End Frame`:
  - `If Video Missing` -> `POST scene video` -> `Upload scene video` -> `Add Scene Video`.
  - `If Voice Missing` -> `POST translate French` -> `Add Script FR` -> `POST French voice` -> `Upload French voice` -> `Add Voice FR`.
- Added idempotency and resilience in workflow:
  - Skip generation when `video_scene` or `voice_fr` already exists.
  - Added retries and `continueOnFail` on external HTTP nodes.
- Validated changes locally:
  - Python syntax compile passed for `modal/image_generator.py`.
  - JSON parse check passed for `n8n/stealing-bones.json`.
- Refactored Modal into focused modules:
  - `modal/app_config.py`, `modal/auth_utils.py`, `modal/request_models.py`
  - `modal/image_endpoint.py`, `modal/video_endpoint.py`, `modal/translation_endpoint.py`, `modal/voice_endpoint.py`
  - `modal/image_generator.py` now acts as a thin entrypoint importing all endpoints.
- Reworked n8n architecture into separate workflows:
  - `n8n/stealing-bones.json` restored to extraction + image generation only.
  - `n8n/video-generation.json` added for Veo scene video generation.
  - `n8n/speech-generation.json` added for French translation + ElevenLabs speech generation.
- Added a concise operations checklist in `n8n/run-checklist.md`.
- Fixed Modal import/runtime issue when deploying endpoint modules individually:
  - Added safe fallback imports in `modal/image_endpoint.py`, `modal/video_endpoint.py`,
    `modal/translation_endpoint.py`, and `modal/voice_endpoint.py`.
  - Each endpoint now bootstraps local `app`/`image`, auth validator, and request models
    if shared modules are not packaged in the container.
- Simplified Modal endpoint modules to fail-fast behavior:
  - Removed all fallback `try/except ModuleNotFoundError` logic from:
    `modal/image_endpoint.py`, `modal/video_endpoint.py`,
    `modal/translation_endpoint.py`, and `modal/voice_endpoint.py`.
  - Restored strict shared imports (`app_config`, `auth_utils`, `request_models`) only.
- Consolidated Modal implementation back to one file:
  - Moved all endpoint code and shared models/helpers into `modal/image_generator.py`.
  - Removed split modules: `modal/app_config.py`, `modal/auth_utils.py`,
    `modal/request_models.py`, `modal/image_endpoint.py`,
    `modal/video_endpoint.py`, `modal/translation_endpoint.py`,
    and `modal/voice_endpoint.py`.
- Fixed Modal video generation model resolution in `modal/image_generator.py`:
  - Replaced default Veo model fallback with `veo-2.0-generate-001` and kept optional `VEO_MODEL_NAME` override.
  - Added explicit handling for unsupported/not-found model errors to return actionable `502` details.
  - Preserved source image MIME type when calling `generate_videos` for better compatibility.
- Fixed scene endpoint keyframe wiring in `modal/image_generator.py`:
  - Added `last_frame` to `GenerateVideosConfig` so `end_image_url` is sent to the model.
  - Kept start frame as `image=` and now pass both keyframes with normalized MIME types.
- Hardened Veo error handling in `modal/image_generator.py`:
  - Fixed SDK compatibility bug by reading GenAI client errors via `.code` (with fallback) instead of `.status_code`.
  - Added automatic fallback: when a model rejects `last_frame`, retry the same request without `last_frame` instead of crashing.
  - Improved `502` details to return stable error code/message across SDK versions.
- Simplified `generate_video` in `modal/image_generator.py` for readability:
  - Consolidated Veo config construction into one helper and removed layered exception branches.
  - Kept only essential handling: 404 model fallback, `last_frame` incompatibility retry, and single `502` mapping for other API client errors.
- Enforced strict keyframe interpolation behavior in `modal/image_generator.py`:
  - `generate_video` now always requires and sends `last_frame`.
  - Removed fallback path that retried without `last_frame`; unsupported models are skipped and endpoint fails if none support end-frame interpolation.
