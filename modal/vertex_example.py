# https://console.cloud.google.com/vertex-ai/studio/saved-prompts/locations/europe-west9/5024337130378231808?model=gemini-3-pro-image-preview&project=yt-short-king&authuser=1

import os

from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        vertexai=True,
        api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
    )

    text1 = types.Part.from_text(
        text="""### REFERENCE ASSETS (Anchor)
{{ $('Airtable - Scenes').item.json.assets }}

### CURRENT SCENE ACTION (Instruction)
{{ $('Airtable - Scenes').item.json.start_image_prompt }}

### FULL SCRIPT CONTEXT
{{ $('Airtable - Project').item.json.script }}"""
    )
    si_text1 = """### Role
You are a specialist in visual continuity for animation. Your job is to generate highly descriptive prompts for a text-to-image generator.

### Character Consistency Logic (IMPORTANT)
1. **Primary Reference:** You will be provided with a Character Reference image and description. Use this as the \"Anchor\" for all generations.
2. **Override Clause:** If the \"Current Scene Action\" explicitly describes a DIFFERENT character design (e.g., \"A new villain appears\" or \"The protagonist transforms into a dragon\"), the Scene Action takes priority over the Reference Image.
3. **Implicit Usage:** If the Scene Action just says \"He walks,\" assume \"He\" is the character from the Reference Image.

### Formatting Rules
- Output ONLY the final prompt for the image generator.
- No conversational filler (e.g., \"Here is your prompt\").
- Style: [Insert your Style, e.g., Studio Ghibli, 3D Render]."""

    model = "gemini-3-pro-image-preview"
    contents = [types.Content(role="user", parts=[text1])]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=32768,
        response_modalities=["TEXT", "IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        system_instruction=[types.Part.from_text(text=si_text1)],
        image_config=types.ImageConfig(
            aspect_ratio="9:16",
            image_size="1K",
            output_mime_type="image/png",
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")


generate()
