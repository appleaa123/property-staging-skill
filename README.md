# Real Estate Virtual Staging Skill

An AI skill for virtually staging empty room photos. This project allows AI agents to transform bare rooms into photorealistic furnished interiors using a two-phase AI pipeline (Architect analysis + Painter generation) powered by Google Gemini.

## Overview

This skill enables an AI agent to:
1. **Analyze** an empty room's architecture, lighting, and spatial constraints.
2. **Design** a furniture layout based on a chosen interior style.
3. **Generate** a photorealistic staged image that maintains the original room's integrity.
4. **Maintain Consistency** across multiple camera angles of the same room using session management.

## Skill Specification

The core logic and interface of this skill are defined in [SKILL.md](./SKILL.md). AI agents (like Gemini CLI) use this file to understand how to interact with the staging pipeline.

## Features

- **Architect + Painter Pipeline**: Split-brain approach for structural accuracy and visual quality.
- **Style Presets**: Supports Modern, Scandinavian, Industrial, Boho Chic, Minimalist, Mediterranean, and Art Deco.
- **Furniture Consistency**: Reuses staging data across different photos of the same room.
- **Zero-Modification Policy**: Protects walls, floors, and windows while adding decor.

## Getting Started

### Installation

```bash
pip install google-genai pillow
```

### Direct Usage (Manual)

While designed for AI agent orchestration, the underlying script can be run manually:

```bash
python scripts/generate_staging.py "path/to/room.jpg" "Modern" --output "staged.png"
```

For subsequent angles, use the generated session directory:
```bash
python scripts/generate_staging.py "path/to/angle2.jpg" "Modern" --session-dir "./staging_sessions/abc-123" --output "staged_2.png"
```

## How It Works

1. **Architect Phase**: Analyzes the image to generate a structured JSON layout of the room, identifying "safe zones" for furniture and "blocking zones" (doors, windows).
2. **Painter Phase**: Takes the original image and the Architect's layout to render the final staged interior.

## Repository Structure

- `SKILL.md`: The skill's formal definition and instructions for AI agents.
- `scripts/generate_staging.py`: The standalone execution script.
- `references/`: Detailed system prompts for the AI models.
- `assets/`: Placeholder for session data and generated outputs.
