import modal
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = modal.App("image-generator")

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "google-genai",
    "fastapi",
    "httpx",
)


def validate_bearer_token(
    authorization: str | None, expected_token: str | None
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )
    token = authorization.replace("Bearer ", "")
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")


class ReferenceImage(BaseModel):
    url: str
    label: str | None = None
    mime_type: str = "image/png"


class ImageRequest(BaseModel):
    assets: str
    creative_direction: str
    image_prompt: str
    script: str
    script_action: str
    reference_images: list[ReferenceImage] = []
    frame_type: str = "start"
    start_frame_url: str | None = None


class VideoRequest(BaseModel):
    project_name: str
    scene_number: int
    script_action: str
    start_image_url: str
    end_image_url: str
    aspect_ratio: str = "9:16"


class TranslateRequest(BaseModel):
    text: str


class FrenchVoiceRequest(BaseModel):
    text: str
    voice_id: str | None = None


SYSTEM_INSTRUCTION_BASE = """\
### Role
You are a specialist in visual continuity for animation. Your job is to GENERATE \
an image for the requested scene - not describe it in text.

### Output Rules (CRITICAL)
- You MUST output an IMAGE. Do NOT output a text description or prompt.
- You may include a very short caption alongside the image, but the image is mandatory.

### Character Consistency Logic (IMPORTANT)
1. **Primary Reference:** You will be provided with Reference Images and a description. \
Use these as the visual "Anchor" for all generations - match their style, colors, and character design.
2. **Override Clause:** If the "Current Scene Action" explicitly describes a DIFFERENT \
character design (e.g., "A new villain appears" or "The protagonist transforms into a \
dragon"), the Scene Action takes priority over the Reference Images.
3. **Implicit Usage:** If the Scene Action just says "He walks," assume "He" is the \
character from the Reference Images.

### Style
- Maintain visual consistency with the provided reference images.
- Match the art style, lighting, and color palette of the references."""

END_FRAME_ADDENDUM = """

### Temporal Continuity (END FRAME)
- You are generating the END frame of a scene. A START frame image is provided.
- The end frame must be visually continuous with the start frame: same characters, \
same environment, same art style, same lighting, same color palette.
- The ONLY differences should come from the scene action (e.g., a character has moved, \
an object has changed state). Everything else must remain consistent.
- Think of start -> end as two keyframes of the same animation."""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-api-key"),
        modal.Secret.from_name("api-auth-token"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def generate_image(data: ImageRequest, authorization: str = Header(None)):
    import os

    import httpx
    from fastapi.responses import Response
    from google import genai
    from google.genai import types

    validate_bearer_token(authorization, os.environ.get("API_AUTH_TOKEN_YT_SHORT"))

    http_client = httpx.Client(timeout=30, follow_redirects=True)

    def _fetch_image(url: str, label: str) -> list[types.Part]:
        try:
            resp = http_client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch image '{label}' from {url}: {exc}",
            )
        return [
            types.Part.from_text(text=f"[Reference image: {label}]"),
            types.Part.from_bytes(data=resp.content, mime_type="image/png"),
        ]

    image_parts: list[types.Part] = []
    for ref in data.reference_images:
        image_parts.extend(_fetch_image(ref.url, ref.label or "reference"))

    start_frame_parts: list[types.Part] = []
    is_end_frame = data.frame_type == "end" and data.start_frame_url
    if is_end_frame:
        start_frame_parts = _fetch_image(data.start_frame_url, "start_frame")

    http_client.close()

    system_text = SYSTEM_INSTRUCTION_BASE + (END_FRAME_ADDENDUM if is_end_frame else "")
    frame_label = "END" if is_end_frame else "START"
    user_prompt = f"""\
### REFERENCE ASSETS & CREATIVE DIRECTION (Anchor)
Assets: {data.assets}
Creative Direction: {data.creative_direction}

### CURRENT SCENE ACTION - {frame_label} FRAME (Instruction)
{data.image_prompt}

### SCRIPT CONTEXT (SOLELY FOR CONTEXT)
Full Script: {data.script}
Scene Script: {data.script_action}"""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [
        types.Content(
            role="user",
            parts=[
                *image_parts,
                *start_frame_parts,
                types.Part.from_text(text=user_prompt),
            ],
        )
    ]
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=32768,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                ),
            ],
            system_instruction=[types.Part.from_text(text=system_text)],
            image_config=types.ImageConfig(aspect_ratio="9:16", image_size="1K"),
        ),
    )

    image_bytes = None
    text_parts: list[str] = []
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
            elif part.text:
                text_parts.append(part.text)

    if not image_bytes:
        raise HTTPException(
            status_code=502,
            detail="Gemini did not return an image. "
            + (f"Text response: {' '.join(text_parts)}" if text_parts else ""),
        )

    headers = {"X-Gemini-Text": " ".join(text_parts)} if text_parts else {}
    return Response(content=image_bytes, media_type="image/png", headers=headers)


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-api-key"),
        modal.Secret.from_name("api-auth-token"),
    ],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def generate_video(data: VideoRequest, authorization: str = Header(None)):
    import os
    import time

    import httpx
    from fastapi.responses import Response
    from google import genai
    from google.genai import types

    validate_bearer_token(authorization, os.environ.get("API_AUTH_TOKEN_YT_SHORT"))

    with httpx.Client(timeout=30, follow_redirects=True) as http_client:
        try:
            start_img = http_client.get(data.start_image_url)
            start_img.raise_for_status()
            end_img = http_client.get(data.end_image_url)
            end_img.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=400, detail=f"Failed to fetch keyframes: {exc}"
            )

    def _normalize_image_mime(raw_content_type: str | None) -> str:
        if not raw_content_type:
            return "image/png"
        return raw_content_type.split(";")[0].strip() or "image/png"

    prompt = f"""\
Project: {data.project_name}
Scene: {data.scene_number}
Action: {data.script_action}

Create one coherent shot that starts on the first image and evolves naturally into the second image.
Keep cinematic quality, stable identity, and smooth transitions.
"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    start_frame = types.Image(
        image_bytes=start_img.content,
        mime_type=_normalize_image_mime(start_img.headers.get("content-type")),
    )
    end_frame = types.Image(
        image_bytes=end_img.content,
        mime_type=_normalize_image_mime(end_img.headers.get("content-type")),
    )

    config = types.GenerateVideosConfig(
        number_of_videos=1,
        aspect_ratio=data.aspect_ratio,
        person_generation="allow_adult",
        negative_prompt="glitch, distortion, text artifacts, abrupt style changes",
        last_frame=end_frame,
    )

    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompt,
        image=start_frame,
        config=config,
    )

    timeout_seconds = 540
    started = time.time()
    while not operation.done:
        if time.time() - started > timeout_seconds:
            raise HTTPException(
                status_code=504, detail="Timed out waiting for Veo result"
            )
        time.sleep(10)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        raise HTTPException(status_code=502, detail="Veo did not return a video")

    generated_video = operation.response.generated_videos[0].video
    if not generated_video:
        raise HTTPException(
            status_code=502, detail="Veo response missing video payload"
        )

    video_bytes = client.files.download(file=generated_video)
    return Response(
        content=video_bytes,
        media_type="video/mp4",
        headers={
            "X-Scene-Number": str(data.scene_number),
            "X-Project-Name": data.project_name,
        },
    )


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-api-key"),
        modal.Secret.from_name("api-auth-token"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def translate_french(data: TranslateRequest, authorization: str = Header(None)):
    import os

    from google import genai
    from google.genai import types

    validate_bearer_token(authorization, os.environ.get("API_AUTH_TOKEN_YT_SHORT"))

    if not data.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=os.environ.get("TRANSLATION_MODEL_NAME", "gemini-2.5-flash"),
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            "Translate this narration into natural French for short-form "
                            "video voice-over. Keep meaning, pacing, and emotional tone. "
                            "Return only the translated text.\n\n"
                            f"Text: {data.text}"
                        )
                    )
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=512,
            response_modalities=["TEXT"],
        ),
    )

    translated = (response.text or "").strip()
    if not translated:
        raise HTTPException(
            status_code=502, detail="No translated text returned by Gemini"
        )

    return JSONResponse(content={"script_fr": translated})


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("api-auth-token"),
        modal.Secret.from_name("elevenlabs-api-key"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def generate_french_voice(data: FrenchVoiceRequest, authorization: str = Header(None)):
    import os

    import httpx
    from fastapi.responses import Response

    validate_bearer_token(authorization, os.environ.get("API_AUTH_TOKEN_YT_SHORT"))

    if not data.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    voice_id = data.voice_id or os.environ.get(
        "ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"
    )
    elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not elevenlabs_api_key:
        raise HTTPException(
            status_code=500, detail="ELEVENLABS_API_KEY is not configured"
        )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": data.text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
            "style": 0.25,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    with httpx.Client(timeout=60) as http_client:
        resp = http_client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs request failed ({resp.status_code}): {resp.text}",
            )

    return Response(content=resp.content, media_type="audio/mpeg")
