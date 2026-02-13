## Short Run Checklist

- [ ] Modal deployed from `modal/image_generator.py` (imports all endpoint modules).
- [ ] Modal secrets present: `gemini-api-key`, `api-auth-token`, `elevenlabs-api-key`.
- [ ] n8n imported workflows:
  - `n8n/stealing-bones.json` (extraction + images only)
  - `n8n/video-generation.json`
  - `n8n/speech-generation.json`
- [ ] Airtable scene fields exist: `start_image`, `end_image`, `video_scene`, `script_fr`, `voice_fr`.
- [ ] n8n `Modal` header credential configured and attached to all Modal HTTP nodes.
- [ ] Run one project with 2-3 scenes and verify outputs per scene:
  - `video_scene` receives MP4 link
  - `script_fr` receives French text
  - `voice_fr` receives MP3 link
- [ ] Re-run once to confirm idempotency:
  - existing `video_scene` skips video branch
  - existing `voice_fr` skips speech branch
