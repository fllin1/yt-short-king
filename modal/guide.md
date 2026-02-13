# Agentic Workflows for n8n

This workspace builds Python-powered API endpoints for n8n workflows using Modal.

## Your Role

When the user describes a workflow they want:

1. **Build** - Write a Modal Python function
2. **Test** - Test locally with `modal run`
3. **Deploy** - Deploy with `modal deploy`
4. **Return** - Give the user their endpoint URL + ready-to-use cURL

**IMPORTANT**:

- Always return a complete cURL command the user can immediately paste into n8n's HTTP Request node.
- **Always implement Bearer token authentication** on all endpoints to prevent unauthorized access.

---

## Initialization for New Users

When a new user provides their Modal token credentials:

1. **Configure Modal authentication**:

   ```bash
   modal token set --token-id <ID> --token-secret <SECRET>
   ```

2. **Verify authentication**:
   - Token will be saved to `~/.modal.toml`
   - Profile name will be displayed (e.g., `username` or `user-12345`)

3. **Ask about their workflow**:
   - "What workflow would you like to build?"
   - Understand inputs, outputs, and any external API requirements
   - Clarify data format and error handling needs

4. **Generate authentication token**:
   - Create a random Bearer token for their endpoint: `openssl rand -hex 32`
   - Store in `.env` as `API_AUTH_TOKEN=<token>`
   - Include this token in all cURL examples and documentation

---

## Modal Setup

### Authentication

Already configured in `~/.modal.toml` (profile: your-modal-profile).

If reconfiguration needed:

1. Go to <https://modal.com/settings> → API Tokens
2. Create new token
3. Run: `modal token set --token-id <ID> --token-secret <SECRET>`

### Existing Secrets (use with `modal.Secret.from_name()`)

- `anthropic-api-key` → `ANTHROPIC_API_KEY`
- `api-auth-token` → `API_AUTH_TOKEN` (Bearer token for endpoint authentication)

### Creating New Secrets

```bash
# Generate a secure random token
openssl rand -hex 32

# Create Modal secret with the token
modal secret create api-auth-token API_AUTH_TOKEN=<your-generated-token>

# Other API secrets
modal secret create my-secret-name API_KEY=xxx ANOTHER_KEY=yyy
```

### Template: Basic HTTP Endpoint

Create a file like `modal_app.py`:

```python
import modal
from fastapi import Header, HTTPException

app = modal.App("my-app-name")
image = modal.Image.debian_slim().pip_install("anthropic", "fastapi", "httpx")  # add deps here

@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("anthropic-api-key"),
        modal.Secret.from_name("api-auth-token")  # Bearer token for endpoint auth
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def my_endpoint(data: dict, authorization: str = Header(None)) -> dict:
    """Describe what this does."""
    import os

    # Bearer token authentication
    expected_token = os.environ.get("API_AUTH_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    # Your logic here
    # Access secrets via os.environ["ANTHROPIC_API_KEY"]
    result = process(data)
    return {"result": result}
```

### Deploy

```bash
cd "/path/to/your/project"
modal deploy modal_app.py
```

Output will show the endpoint URL like:

```
https://your-modal-profile--my-app-name-my-endpoint.modal.run
```

### Test Locally (without deploying)

```bash
modal run modal_app.py::my_endpoint --data '{"key": "value"}'
```

### Return to User

After deployment, give the user:

1. **Endpoint URL**: `https://your-modal-profile--{app-name}-{function-name}.modal.run`
2. **Bearer Token**: `<the token from .env>`
3. **cURL command** ready to paste:

```bash
curl -X POST "https://your-modal-profile--my-app-name-my-endpoint.modal.run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"your": "payload"}'
```

1. **n8n HTTP Request node config**:
   - Method: POST
   - URL: the endpoint
   - Authentication: Header Auth
     - Name: `Authorization`
     - Value: `Bearer YOUR_TOKEN_HERE`
   - Body: JSON

---

## Project Structure

```
modal_app.py          # Main Modal deployment (add functions here or create new files)
.env                  # Local environment variables (gitignored)
.env.example          # Template for .env
image_generator.py    # Gemini image generation endpoint
```

**Security**: All endpoints must implement Bearer token authentication as shown in the templates above. Never deploy an endpoint without authentication.

---

## Example Endpoints

### Scene Image Generator

**File**: `modal/image_generator.py`
**App**: `image-generator`
**Endpoint**: `POST https://naviredelest--image-generator-generate-image.modal.run`

**Purpose**: Generate scene images for YouTube Shorts using Gemini 3 Pro Image Preview. Accepts a scene prompt, reference assets, and the full script context, then returns a base64-encoded PNG (9:16 portrait, 1K).

**Secrets used**: `gemini-api-key`, `api-auth-token`

**Input**:

```json
{
  "assets": "Character: young knight, silver armor, blue cape...",
  "image_prompt": "The knight draws his sword in a dark cave",
  "script": "Full script of the YouTube Short for context...",
  "reference_images": [
    { "url": "https://dl.airtable.com/.../character.png", "label": "core_image" },
    { "url": "https://dl.airtable.com/.../elements.png", "label": "core_elements", "mime_type": "image/png" }
  ],
  "frame_type": "start",
  "start_frame_url": null
}
```

- `assets` (string): Reference assets / character description — the visual "anchor"
- `image_prompt` (string): The specific scene action to illustrate (start or end frame prompt)
- `script` (string): Full script for narrative context
- `reference_images` (array, optional): Airtable attachment URLs to include as visual references for Gemini
  - `url` (string, required): Direct URL to the image
  - `label` (string, optional): Label shown to the model (e.g. "core_image")
  - `mime_type` (string, default "image/png"): MIME type of the image
- `frame_type` (string, default `"start"`): Either `"start"` or `"end"`. When `"end"`, the model receives temporal continuity instructions.
- `start_frame_url` (string, optional): URL of the previously generated start frame image. Used when `frame_type="end"` to ensure visual continuity between keyframes.

**Output**:

- **Body**: Raw PNG binary (`Content-Type: image/png`)
- **Header** `X-Gemini-Text`: Any text the model returned alongside the image (optional)

**Deploy**:

```bash
cd modal/
modal deploy image_generator.py
```

**cURL**:

```bash
curl -X POST "https://naviredelest--image-generator-generate-image.modal.run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "assets": "Character: young knight, silver armor, blue cape",
    "image_prompt": "The knight draws his sword in a dark cave",
    "script": "A young knight ventures into a dark cave to face a dragon...",
    "reference_images": [
      {"url": "https://dl.airtable.com/.../character.png", "label": "core_image"}
    ]
  }' \
  --output scene.png
```

**n8n HTTP Request node config**:

- **Method**: POST
- **URL**: `https://naviredelest--image-generator-generate-image.modal.run`
- **Authentication**: Header Auth
  - Name: `Authorization`
  - Value: `Bearer YOUR_TOKEN_HERE`
- **Body**: JSON with the following expression fields (mapped from Airtable):
  - `assets`: `{{ $('Search image prompts').item.json.assets }}`
  - `image_prompt`: `{{ $json.start_image_prompt }}` (or `end_image_prompt` for end frame)
  - `script`: `{{ $('Search project script').item.json.script }}`
  - `reference_images`: Array of Airtable attachment objects mapped to `{ "url": ..., "label": ... }` (see n8n example below)
- **Response**: Raw PNG binary. n8n automatically captures this as a binary property (`data`), which can be piped directly to Google Drive Upload, Airtable, etc. — no conversion needed.

**n8n body examples**:

Start frame request:

```json
{
  "assets": "={{ $('Search image prompts').item.json.assets }}",
  "image_prompt": "={{ $json.start_image_prompt }}",
  "script": "={{ $('Search project script').item.json.script }}",
  "frame_type": "start",
  "reference_images": [
    { "url": "={{ $json.core_image[0].url }}", "label": "core_image" },
    { "url": "={{ $json.core_elements[0].url }}", "label": "core_elements" }
  ]
}
```

End frame request (includes the start frame for continuity):

```json
{
  "assets": "={{ $('Search image prompts').item.json.assets }}",
  "image_prompt": "={{ $('Search image prompts').item.json.end_image_prompt }}",
  "script": "={{ $('Search project script').item.json.script }}",
  "frame_type": "end",
  "start_frame_url": "={{ $('Google Drive Upload Start').item.json.webContentLink }}",
  "reference_images": [
    { "url": "={{ $json.core_image[0].url }}", "label": "core_image" },
    { "url": "={{ $json.core_elements[0].url }}", "label": "core_elements" }
  ]
}
```

---

### Email Reply Generator (Example)

**Endpoint**: `POST https://your-modal-profile--email-reply-generate-reply.modal.run`

**Purpose**: Generate AI-powered email replies based on conversation history

**Input**:

```json
{
  "html": [
    "<div>Newest email (their reply)</div>",
    "<div>Previous email</div>",
    "<div>Oldest email (our initial outreach)</div>"
  ],
  "sender_email": "user@example.com"
}
```

- `html`: Array of email HTML strings, **newest first, oldest last**
- Last item is always "us" (our outreach), then alternates them/us going backwards
- `sender_email`: Optional. Used for conditional logic in reply generation

**Output**:

```json
{
  "reply": "Hey [Name],\n\nThank you for getting back to me!..."
}
```

**cURL**:

```bash
curl -X POST "https://your-modal-profile--email-reply-generate-reply.modal.run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "html": ["<div>Their reply</div>", "<div>Our initial email</div>"],
    "sender_email": "user@example.com"
  }'
```

---

## Common Patterns

### AI/LLM Endpoint (Claude)

```python
import modal
from fastapi import Header, HTTPException

app = modal.App("ai-task")
image = modal.Image.debian_slim().pip_install("anthropic", "fastapi")

@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("anthropic-api-key"),
        modal.Secret.from_name("api-auth-token")
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def process(data: dict, authorization: str = Header(None)) -> dict:
    import anthropic
    import os

    # Bearer token authentication
    expected_token = os.environ.get("API_AUTH_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-5-20251101",  # or claude-sonnet-4-20250514
        max_tokens=1024,
        messages=[{"role": "user", "content": data.get("prompt", "")}],
        system="Your system prompt here"
    )

    return {"response": message.content[0].text}
```

### Web Scraping Endpoint

```python
import modal
from fastapi import Header, HTTPException

app = modal.App("scraper")
image = modal.Image.debian_slim().pip_install("httpx", "beautifulsoup4", "fastapi")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("api-auth-token")],
    timeout=60
)
@modal.fastapi_endpoint(method="POST")
def scrape(data: dict, authorization: str = Header(None)) -> dict:
    import httpx
    from bs4 import BeautifulSoup
    import os

    # Bearer token authentication
    expected_token = os.environ.get("API_AUTH_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    url = data.get("url")
    response = httpx.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    return {"title": soup.title.string, "text": soup.get_text()[:1000]}
```

### Data Processing Endpoint

```python
import modal
from fastapi import Header, HTTPException

app = modal.App("processor")
image = modal.Image.debian_slim().pip_install("pandas", "fastapi")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("api-auth-token")],
    timeout=300
)
@modal.fastapi_endpoint(method="POST")
def process_data(data: dict, authorization: str = Header(None)) -> dict:
    import pandas as pd
    import os

    # Bearer token authentication
    expected_token = os.environ.get("API_AUTH_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    # data contains your input
    df = pd.DataFrame(data.get("records", []))
    result = df.describe().to_dict()

    return {"stats": result}
```

---

## Environment Variables

### Local (.env file)

```
ANTHROPIC_API_KEY=sk-ant-api03-xxx
OPENAI_API_KEY=sk-xxx
```

### Modal Secrets

Create once, use everywhere:

```bash
modal secret create anthropic-api-key ANTHROPIC_API_KEY=sk-ant-xxx
modal secret create openai-api-key OPENAI_API_KEY=sk-xxx
```

Use in code:

```python
@app.function(secrets=[modal.Secret.from_name("anthropic-api-key")])
def my_func():
    import os
    key = os.environ["ANTHROPIC_API_KEY"]
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `modal deploy modal_app.py` | Deploy to Modal |
| `modal run modal_app.py::func_name` | Test locally |
| `modal secret create name KEY=value` | Create secret |
| `modal secret list` | List secrets |
| `modal app list` | List deployed apps |
| `modal app stop app-name` | Stop an app |

---

## Checklist for Each New Endpoint

- [ ] Create function in `modal_app.py` (or new file)
- [ ] Add required pip packages to image
- [ ] Add required secrets
- [ ] Test locally with `modal run`
- [ ] Deploy with `modal deploy`
- [ ] Return to user: endpoint URL + cURL + n8n config
