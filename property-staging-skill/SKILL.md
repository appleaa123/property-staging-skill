---
name: real-estate-staging
description: >
  Virtually stage empty room photos for real estate listings. Transforms bare rooms into
  photorealistic furnished interiors using a two-phase AI pipeline (Architect analysis +
  Painter generation) powered by Google Gemini. Use this skill whenever a user wants to
  stage a room, furnish an empty space, generate a virtual staging image, or make a room
  look lived-in for real estate or interior design purposes — even if they don't say
  "staging" explicitly. Supports multiple angles of the same room with furniture
  consistency. Requires GOOGLE_API_KEY environment variable.
---

# Real Estate Virtual Staging Skill

Transforms empty room photos into professionally staged interiors without modifying the room's architecture. Uses a two-phase "Architect + Painter" pipeline: first analyze the room's structure and constraints, then generate a photorealistic staged image.

## Gather Input

Before running, collect:

1. **Image path** — absolute or relative path to the empty room photo (JPG, PNG, WEBP)
2. **Style** — ask if not provided. Options:
   - `Modern` · `Scandinavian` · `Industrial` · `Boho Chic` · `Minimalist` · `Mediterranean` · `Art Deco`
3. **Room type** (optional) — auto-detected if omitted. E.g. Living Room, Kitchen, Bedroom
4. **Custom instructions** (optional) — user preferences like "add a piano" or "keep it minimal"
5. **Session dir** (optional) — for a 2nd+ angle of the same room, reuse the session directory printed after the first run

## Run the Staging Script

```bash
# First image (anchor)
python property-staging-skill/scripts/generate_staging.py \
  "/path/to/room.jpg" "Modern" \
  --output staged_living_room.png

# Additional angles of the same room (pass --session-dir from prior run)
python property-staging-skill/scripts/generate_staging.py \
  "/path/to/room_angle2.jpg" "Modern" \
  --session-dir ./staging_sessions/abc-123 \
  --output staged_angle2.png

# With all options
python property-staging-skill/scripts/generate_staging.py \
  "/path/to/room.jpg" "Scandinavian" \
  --room-type "Bedroom" \
  --custom "Add a vintage reading chair in the corner" \
  --output staged_bedroom.png
```

**Requires:** `GOOGLE_API_KEY` environment variable set to a valid Google AI API key.

**Install dependencies if needed:**
```bash
pip install google-genai pillow
```

## Handle the Output

The script prints step-by-step progress and ends with:
```
Session directory: ./staging_sessions/abc-123
Output: staged_living_room.png
```

- Show the user the output image path and offer to open/display it
- Save the session directory — the user will need it to stage additional angles
- If the user has more angles of the same room, run again with `--session-dir`

## Multi-Angle Workflow

For multiple camera angles of the same room:

1. **First angle**: Run without `--session-dir`. The script creates a session and prints its path.
2. **Subsequent angles**: Run with `--session-dir ./staging_sessions/<id>`. The script loads the furniture inventory from the first staged image to maintain consistency.

Furniture style, colors, and spatial alignment are preserved across angles automatically.

## Design Principles (For User Context)

- **Architecture is immutable** — walls, floors, ceilings, doors, windows are never changed
- **Blocking rules are enforced** — doors and windows are always kept visible; countertops can hold decor
- **Perspective-accurate** — furniture is scaled and aligned to the camera angle
- **Zone-aware** — open-concept spaces (e.g., Kitchen + Living Room) are staged with appropriate furniture in each zone

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `GOOGLE_API_KEY not set` | Set the env var: `export GOOGLE_API_KEY=your_key` |
| `File not found` | Use absolute path to the image |
| `No image generated` | Gemini rate limit — wait 30s and retry |
| Style not recognized | Use one of the 7 exact style names above |
