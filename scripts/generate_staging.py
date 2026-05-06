"""
Real Estate Virtual Staging - Standalone Script
Two-phase pipeline: Architect (room analysis) → Painter (image generation)
Supports multi-angle sessions for furniture consistency across camera angles.

Usage:
  python generate_staging.py <image> <style> [--room-type X] [--session-dir ./sessions/id]
                             [--output out.png] [--custom "..."]
"""
import os
import sys
import json
import uuid
import argparse
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
ARCHITECT_MODEL = "gemini-2.5-pro"
PAINTER_MODEL = "gemini-2.5-flash-preview-05-20"

# ---------------------------------------------------------------------------
# Style database
# ---------------------------------------------------------------------------
STYLE_ALIASES = {
    "japandi": "Minimalist",
    "mid-century": "Modern",
    "mid century": "Modern",
    "coastal": "Scandinavian",
    "farmhouse": "Scandinavian",
    "contemporary": "Modern",
    "luxury": "Modern",
    "rustic": "Industrial",
    "eclectic": "Boho Chic",
    "bohemian": "Boho Chic",
    "classic": "Mediterranean",
}

STYLE_DATABASE = {
    "Modern": {
        "Living Room": {
            "furniture": ["low-profile sectional sofa", "glass coffee table", "geometric area rug", "arc floor lamp", "media console", "accent armchair"],
            "layout_instructions": [
                "Place sofa facing the focal point or main window.",
                "Define the seating area with a rug — rug should anchor all seating.",
                "Keep lines clean and horizontal; avoid ornate or curved pieces.",
                "CRITICAL: Do not place kitchen or dining items in this space.",
            ],
        },
        "Kitchen": {
            "furniture": ["wooden cutting board", "ceramic fruit bowl", "potted herbs", "runner rug", "countertop vase", "small cookbook stack"],
            "layout_instructions": [
                "Keep the center of the room OPEN and clear.",
                "Place decor items ONLY on existing countertops.",
                "CRITICAL: DO NOT ADD ISLANDS or tables in the middle of the floor.",
                "CRITICAL: Never place sofas or living room furniture here.",
            ],
        },
        "Dining Room": {
            "furniture": ["rectangular dining table", "upholstered dining chairs", "pendant light", "sideboard", "centerpiece vase"],
            "layout_instructions": [
                "Center the dining table under any overhead fixture.",
                "Allow 90 cm clearance around all sides of the table.",
                "CRITICAL: Do not blend with kitchen island features.",
            ],
        },
        "Bedroom": {
            "furniture": ["platform bed", "pair of nightstands", "soft area rug", "modern dresser", "reading lamp", "accent chair"],
            "layout_instructions": [
                "Center bed on the longest unobstructed wall.",
                "Nightstands flank both sides symmetrically.",
                "Rug extends under the lower two-thirds of the bed.",
            ],
        },
        "Bathroom": {
            "furniture": ["plush bath mat", "folded towels", "soap dispenser set", "small potted plant", "vanity tray with toiletries"],
            "layout_instructions": [
                "Only place movable decor items.",
                "CRITICAL: DO NOT ADD OR CHANGE PLUMBING FIXTURES (sinks, toilets, showers, tubs).",
                "Keep floor mostly clear for movement.",
            ],
        },
        "Office": {
            "furniture": ["sleek writing desk", "ergonomic chair", "table lamp", "small bookshelf", "area rug", "desk plant"],
            "layout_instructions": [
                "Face desk towards room center or window for natural light.",
                "CRITICAL: Do not add beds or large sofas.",
            ],
        },
        "Storage/Entry": {
            "furniture": ["slim console table", "entryway bench", "coat rack", "runner rug", "wall mirror"],
            "layout_instructions": [
                "Keep pathways completely clear.",
                "CRITICAL: Do not block doorways or entryways.",
                "Do not add large furniture pieces.",
            ],
        },
    },
    "Scandinavian": {
        "Living Room": {
            "furniture": ["light oak sofa with white cushions", "birch wood coffee table", "sheepskin throw rug", "floor lamp with linen shade", "minimalist bookshelf", "knit throw blanket"],
            "layout_instructions": [
                "Maximize natural light — keep window areas clear.",
                "Use neutral whites, greys, and natural wood tones.",
                "Leave negative space; do not overcrowd.",
                "Place a cozy reading nook near the window if space allows.",
            ],
        },
        "Kitchen": {
            "furniture": ["wooden chopping board", "white ceramic pitcher with stems", "small potted succulent", "linen dish towel", "birch wood bowl with fruit"],
            "layout_instructions": [
                "Keep surfaces minimal — less is more.",
                "Place natural materials (wood, ceramic) on countertops only.",
                "CRITICAL: DO NOT ADD ISLANDS or tables in the middle of the floor.",
            ],
        },
        "Dining Room": {
            "furniture": ["round birch dining table", "white wishbone chairs", "pendant lamp in natural materials", "small vase with dried flowers"],
            "layout_instructions": [
                "Opt for round or oval table for intimate gatherings.",
                "Center table in the room.",
            ],
        },
        "Bedroom": {
            "furniture": ["low linen-upholstered bed", "pair of floating nightstands", "white fluffy area rug", "simple wooden dresser", "pendant bedside lamps"],
            "layout_instructions": [
                "Use all-white or soft grey bedding.",
                "Keep nightstands simple with minimal decor.",
                "Rug should be light and textured (sheepskin, wool).",
            ],
        },
        "Bathroom": {
            "furniture": ["fluffy white bath mat", "stacked white towels", "small wooden stool", "potted eucalyptus", "simple soap dish"],
            "layout_instructions": [
                "Only movable decor; no plumbing changes.",
                "Emphasize clean, spa-like simplicity.",
            ],
        },
        "Office": {
            "furniture": ["light oak desk", "ergonomic chair in light grey", "small potted plant", "minimalist desk lamp", "woven storage basket"],
            "layout_instructions": ["Keep desk surface clear; only essentials visible."],
        },
        "Storage/Entry": {
            "furniture": ["wooden bench with cushion", "minimal coat hooks", "jute runner rug", "potted plant", "simple wall mirror"],
            "layout_instructions": ["Keep entryway light, airy, and clutter-free."],
        },
    },
    "Industrial": {
        "Living Room": {
            "furniture": ["brown leather sofa", "reclaimed wood coffee table", "metal floor lamp", "exposed-brick-tone area rug", "vintage metal bookshelf", "leather accent chair"],
            "layout_instructions": [
                "Use raw materials — leather, metal, reclaimed wood.",
                "Expose structural elements; don't hide them.",
                "Darker, moodier palette: charcoal, rust, dark brown.",
                "CRITICAL: Keep layout open; avoid cluttering with too many pieces.",
            ],
        },
        "Kitchen": {
            "furniture": ["cast iron pan on counter", "metal utensil holder", "dark ceramic bowls", "industrial pendant light (if movable)", "bar stool (only if island already exists)"],
            "layout_instructions": [
                "Dark countertop accessories only.",
                "CRITICAL: DO NOT ADD ISLANDS or tables; only decorate existing surfaces.",
            ],
        },
        "Dining Room": {
            "furniture": ["reclaimed wood dining table", "metal cross-back chairs", "Edison bulb pendant", "industrial sideboard"],
            "layout_instructions": [
                "Table should feel heavy and grounded.",
                "Metal and wood contrast is key.",
            ],
        },
        "Bedroom": {
            "furniture": ["metal-frame bed", "dark wood nightstands", "industrial floor lamp", "distressed leather bench", "exposed-pipe clothes rack"],
            "layout_instructions": [
                "Use dark, moody bedding (charcoal, deep navy).",
                "Metal frame should be visible and featured.",
            ],
        },
        "Bathroom": {
            "furniture": ["dark bath mat", "rolled dark towels", "matte black soap dispenser", "small succulent", "metal shelf with toiletries"],
            "layout_instructions": ["No plumbing changes; matte black accessories only."],
        },
        "Office": {
            "furniture": ["metal and wood desk", "leather rolling chair", "metal task lamp", "industrial pipe shelving", "concrete-look desk organizer"],
            "layout_instructions": ["Raw, functional workspace — everything has a purpose."],
        },
        "Storage/Entry": {
            "furniture": ["metal coat rack", "reclaimed wood console", "dark runner mat", "vintage trunk as bench"],
            "layout_instructions": ["Keep entry functional and utilitarian."],
        },
    },
    "Boho Chic": {
        "Living Room": {
            "furniture": ["low rattan sofa with colorful cushions", "macramé wall hanging", "layered area rugs", "floor poufs", "hanging plants", "wicker side table", "floor cushions"],
            "layout_instructions": [
                "Layer rugs of different textures and patterns.",
                "Mix patterns freely but maintain a warm color palette (terracotta, ochre, rust).",
                "Add plants at varying heights — hanging, floor, shelf.",
                "Furniture should feel low and relaxed.",
            ],
        },
        "Kitchen": {
            "furniture": ["woven fruit basket", "potted herbs in terracotta pots", "colorful ceramic bowls", "macramé hanging planter", "woven placemats"],
            "layout_instructions": [
                "Warm, earthy tones on all surfaces.",
                "CRITICAL: DO NOT ADD ISLANDS.",
                "Layer textures: woven, ceramic, wood.",
            ],
        },
        "Dining Room": {
            "furniture": ["rattan dining chairs", "wooden dining table", "woven table runner", "eclectic centerpiece", "hanging plants"],
            "layout_instructions": ["Mismatched chairs are intentional and encouraged."],
        },
        "Bedroom": {
            "furniture": ["low platform bed with layered bedding", "rattan nightstands", "macramé headboard or wall hanging", "layered rugs", "hanging plants", "floor cushions"],
            "layout_instructions": [
                "Layer bedding with different textures and patterns.",
                "Keep it cozy and lived-in.",
            ],
        },
        "Bathroom": {
            "furniture": ["woven bath mat", "terracotta pot plant", "rolled towels in basket", "wooden accessories", "dried pampas grass"],
            "layout_instructions": ["Warm, organic, natural materials only."],
        },
        "Office": {
            "furniture": ["rattan desk", "eclectic chair with cushion", "hanging plants", "woven rug", "collection of books and plants"],
            "layout_instructions": ["Layered, personal, creative feel."],
        },
        "Storage/Entry": {
            "furniture": ["rattan bench", "macramé wall hanging", "layered runner rug", "potted snake plant", "woven basket"],
            "layout_instructions": ["Warm and welcoming; personality from day one."],
        },
    },
    "Minimalist": {
        "Living Room": {
            "furniture": ["simple linen sofa in neutral tone", "low square coffee table", "single large area rug", "one floor lamp", "small side table"],
            "layout_instructions": [
                "Every item must earn its place — if in doubt, leave it out.",
                "Maximum 5 furniture pieces total.",
                "No decorative objects unless functional.",
                "Palette: white, off-white, light grey, natural wood only.",
            ],
        },
        "Kitchen": {
            "furniture": ["single cutting board", "small plant in white ceramic pot", "one clean dish towel"],
            "layout_instructions": [
                "Countertops must look nearly empty.",
                "CRITICAL: DO NOT ADD ISLANDS.",
                "Hide everything not in immediate use.",
            ],
        },
        "Dining Room": {
            "furniture": ["simple rectangular table", "matching chairs (no extras)", "single small centerpiece"],
            "layout_instructions": ["Table should look like it seats exactly the right number of people."],
        },
        "Bedroom": {
            "furniture": ["low bed frame", "one nightstand", "minimal bedding in white or grey", "small lamp"],
            "layout_instructions": [
                "No clutter whatsoever.",
                "Single piece of art maximum on walls.",
            ],
        },
        "Bathroom": {
            "furniture": ["plain white bath mat", "neatly folded white towels", "single soap dispenser"],
            "layout_instructions": ["Absolute minimum — if it doesn't need to be there, remove it."],
        },
        "Office": {
            "furniture": ["clean white desk", "simple chair", "single lamp", "one small plant"],
            "layout_instructions": ["Completely clear desktop except for one functional item."],
        },
        "Storage/Entry": {
            "furniture": ["single slim console table", "one mirror", "minimal runner"],
            "layout_instructions": ["Nothing on the floor except the rug."],
        },
    },
    "Mediterranean": {
        "Living Room": {
            "furniture": ["terracotta-colored sofa", "mosaic-patterned coffee table", "layered colorful area rugs", "wrought iron floor lamp", "ceramic vases", "arched mirror"],
            "layout_instructions": [
                "Rich warm colors: terracotta, cobalt blue, ochre, deep red.",
                "Mix patterns — tiles, stripes, florals work together.",
                "Add plants and natural elements throughout.",
                "Furniture should feel heavy, crafted, artisanal.",
            ],
        },
        "Kitchen": {
            "furniture": ["terracotta pot with herbs", "colorful ceramic fruit bowl", "mosaic tile trivet (on counter)", "woven basket", "olive oil bottles as decor"],
            "layout_instructions": [
                "Warm, sun-soaked accessories on countertops.",
                "CRITICAL: DO NOT ADD ISLANDS.",
                "Blue and white ceramics work well.",
            ],
        },
        "Dining Room": {
            "furniture": ["heavy wooden dining table", "wrought iron chairs with cushions", "ceramic centerpiece bowl", "hanging iron light fixture", "sideboard with pottery"],
            "layout_instructions": [
                "Table should feel like a gathering place for family meals.",
                "Mix wood and iron.",
            ],
        },
        "Bedroom": {
            "furniture": ["carved wooden bed frame", "colorful textile bedding", "iron bedside lamps", "mosaic side tables", "arched floor mirror", "potted olive tree"],
            "layout_instructions": [
                "Rich jewel-tone bedding: deep blues, terracottas, golds.",
                "Bed frame should be ornate or carved.",
            ],
        },
        "Bathroom": {
            "furniture": ["colorful patterned bath mat", "terracotta pot with plant", "mosaic soap dish", "decorative ceramic jars", "rolled colored towels"],
            "layout_instructions": ["No plumbing changes; use colorful handmade-style accessories."],
        },
        "Office": {
            "furniture": ["solid wood desk", "leather chair", "terracotta plant pot", "mosaic paperweight", "woven rug"],
            "layout_instructions": ["Warm, scholarly, handcrafted feel."],
        },
        "Storage/Entry": {
            "furniture": ["painted tile-top console table", "wrought iron coat hooks", "colorful runner", "large terracotta pot with plant", "arched mirror"],
            "layout_instructions": ["Welcoming, warm, sun-drenched feel from the entrance."],
        },
    },
    "Art Deco": {
        "Living Room": {
            "furniture": ["velvet sofa in deep jewel tone (emerald, navy, burgundy)", "geometric gold coffee table", "art deco area rug with bold patterns", "brass floor lamp", "mirrored side table", "statement art piece"],
            "layout_instructions": [
                "Bold geometric patterns on rug and upholstery.",
                "Gold and brass metallic accents throughout.",
                "Rich jewel tones: emerald green, sapphire blue, deep burgundy.",
                "Every piece should feel glamorous and intentional.",
            ],
        },
        "Kitchen": {
            "furniture": ["brass fruit bowl", "gold-rimmed ceramic vase", "geometric canister set", "black and gold kitchen accessories"],
            "layout_instructions": [
                "Metallic gold and black accessories on countertops.",
                "CRITICAL: DO NOT ADD ISLANDS.",
                "Less is more — each piece must be striking.",
            ],
        },
        "Dining Room": {
            "furniture": ["glossy dark wood dining table", "upholstered chairs in jewel-tone velvet", "geometric chandelier", "mirrored sideboard", "gold candle holders"],
            "layout_instructions": [
                "Table should look like a black tie dinner setting.",
                "Gold accents everywhere.",
            ],
        },
        "Bedroom": {
            "furniture": ["upholstered bed in velvet (emerald or navy)", "mirrored nightstands", "brass table lamps", "geometric area rug", "ornate floor mirror", "velvet bench at foot of bed"],
            "layout_instructions": [
                "Bed should be the glamorous centerpiece.",
                "Symmetrical arrangement is key.",
            ],
        },
        "Bathroom": {
            "furniture": ["black and gold bath mat", "gold soap dispenser", "geometric marble tray", "art deco candle", "bold patterned towels"],
            "layout_instructions": ["No plumbing changes; gold and black accessories create the look."],
        },
        "Office": {
            "furniture": ["lacquered dark desk", "tufted leather chair", "brass desk lamp", "geometric bookends", "velvet rug"],
            "layout_instructions": ["Feels like a 1920s publisher's private office."],
        },
        "Storage/Entry": {
            "furniture": ["glossy console table", "geometric brass mirror", "bold patterned runner", "dramatic floor plant in gold pot"],
            "layout_instructions": ["First impression should be dramatic and glamorous."],
        },
    },
}

CATEGORY_MAP = {
    "Living room": "Living Room", "Family room": "Living Room", "Great room": "Living Room",
    "Parlor": "Living Room", "Sunroom": "Living Room", "Den": "Living Room",
    "Kitchen": "Kitchen", "Pantry": "Kitchen", "Scullery": "Kitchen",
    "Laundry room": "Utility", "Utility room": "Utility",
    "Primary bedroom": "Bedroom", "Guest room": "Bedroom", "Nursery": "Bedroom",
    "Kids room": "Bedroom", "Kids' room": "Bedroom",
    "Bathroom": "Bathroom", "Powder room": "Bathroom",
    "Dining room": "Dining Room",
    "Home office": "Office", "Study": "Office", "Library": "Office",
    "Game room": "Leisure", "Home theater": "Leisure",
    "Gym": "Gym", "Exercise room": "Gym",
    "Foyer": "Storage/Entry", "Entryway": "Storage/Entry", "Mudroom": "Storage/Entry",
    "Hallway": "Storage/Entry",
}

ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "room_type": {"type": "STRING"},
        "visible_zones": {"type": "ARRAY", "items": {"type": "STRING"}},
        "fixed_elements": {"type": "ARRAY", "items": {"type": "STRING"}},
        "floor_material": {"type": "STRING"},
        "lighting_source": {"type": "STRING"},
        "perspective_notes": {"type": "STRING"},
        "blocking_rules": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "element_name": {"type": "STRING"},
                    "blocking_rule": {
                        "type": "STRING",
                        "enum": ["can_block", "cannot_block", "can_place_on_top"],
                    },
                },
                "required": ["element_name", "blocking_rule"],
            },
        },
        "spatial_layout": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "subject": {"type": "STRING"},
                    "relation": {"type": "STRING"},
                    "object": {"type": "STRING"},
                },
                "required": ["subject", "relation", "object"],
            },
        },
    },
    "required": [
        "room_type", "visible_zones", "fixed_elements", "floor_material",
        "lighting_source", "perspective_notes", "blocking_rules", "spatial_layout",
    ],
}


def _resolve_style(style: str) -> str:
    """Normalize style name, applying aliases for common variations."""
    key = style.lower().strip()
    if key in STYLE_ALIASES:
        return STYLE_ALIASES[key]
    # Title-case exact match
    titled = style.title()
    if titled in STYLE_DATABASE:
        return titled
    # Partial match
    for db_style in STYLE_DATABASE:
        if db_style.lower() in key or key in db_style.lower():
            return db_style
    print(f"Warning: Unknown style '{style}', falling back to Modern.")
    return "Modern"


def _resolve_room_category(room_type: str) -> str:
    """Map specific room names to style DB categories."""
    if room_type in STYLE_DATABASE.get("Modern", {}):
        return room_type
    mapped = CATEGORY_MAP.get(room_type)
    if mapped:
        return mapped
    lower = room_type.lower()
    for key, val in CATEGORY_MAP.items():
        if key.lower() in lower or lower in key.lower():
            return val
    return "Living Room"


def _sanitize_blocking_rules(analysis: dict) -> dict:
    """
    Ensures each blocking_rule is a single string, not a list.
    Gemini occasionally returns ambiguous elements as a list.
    Priority when converting: cannot_block > can_place_on_top > can_block
    """
    priority = ["cannot_block", "can_place_on_top", "can_block"]
    rules = analysis.get("blocking_rules", [])
    sanitized = []
    for rule in rules:
        br = rule.get("blocking_rule")
        if isinstance(br, list):
            chosen = next((p for p in priority if p in br), br[0] if br else "can_block")
            rule = {**rule, "blocking_rule": chosen}
        sanitized.append(rule)
    return {**analysis, "blocking_rules": sanitized}


def architect_analyze(client: genai.Client, image_bytes: bytes, room_type: Optional[str] = None) -> dict:
    """Phase 1: Analyze room structure using Gemini Pro."""
    print("  [Architect] Analyzing room structure...")
    prompt = f"""Analyze this empty room for virtual staging.
Primary focus: {room_type or 'Determine automatically'}.

Instructions:
1. Identify all permanent structural elements (Doors, Doorways, Windows, Islands, Built-in Cabinets, Appliances).
2. Assign blocking_rule for each element:
   - cannot_block: doors, windows, doorways, appliances (must always remain visible)
   - can_place_on_top: countertops, islands, shelves (surfaces that can hold decor)
   - can_block: walls, columns (furniture may be placed in front)
3. blocking_rule MUST be exactly ONE string value from the enum. NEVER an array.
4. Map spatial layout — relative positions of elements (e.g., subject: "Door", relation: "is left of", object: "Window").
5. Note the exact camera perspective and angle.
"""
    response = client.models.generate_content(
        model=ARCHITECT_MODEL,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ANALYSIS_SCHEMA,
            temperature=0.1,
        ),
    )
    analysis = json.loads(response.text)
    analysis = _sanitize_blocking_rules(analysis)
    detected = analysis.get("room_type", room_type or "Room")
    print(f"  [Architect] Detected: {detected} | Fixed elements: {len(analysis.get('fixed_elements', []))} | Blocking rules: {len(analysis.get('blocking_rules', []))}")
    return analysis


def get_style_instructions(style: str, room_type: str, visible_zones: list) -> list:
    """Look up layout instructions from the inlined style database."""
    resolved_style = _resolve_style(style)
    style_data = STYLE_DATABASE[resolved_style]
    category = _resolve_room_category(room_type)

    data = style_data.get(category) or style_data.get("Living Room", {})
    instructions = list(data.get("layout_instructions", []))

    for zone in visible_zones:
        zone_cat = _resolve_room_category(zone)
        zone_data = style_data.get(zone_cat)
        if zone_data:
            for rule in zone_data.get("layout_instructions", []):
                instructions.append(f"IN {zone.upper()} ZONE: {rule}")

    return instructions


def painter_stage(
    client: genai.Client,
    image_bytes: bytes,
    style: str,
    analysis: dict,
    layout_instructions: list,
    inventory: Optional[str] = None,
    custom_instructions: Optional[str] = None,
) -> bytes:
    """Phase 2: Generate staged image using Gemini Flash image model."""
    print(f"  [Painter] Generating staged image in {style} style...")

    room_type = analysis.get("room_type", "Room")
    visible_zones = analysis.get("visible_zones", [])
    fixed_elements = analysis.get("fixed_elements", [])
    blocking_rules = analysis.get("blocking_rules", [])
    spatial_layout = analysis.get("spatial_layout", [])

    # Separate blocking rule categories
    cannot_block = [br for br in blocking_rules if br.get("blocking_rule") == "cannot_block"]
    can_place_on_top = [br for br in blocking_rules if br.get("blocking_rule") == "can_place_on_top"]

    # Protected elements string (excluding generic architectural terms)
    skip_generic = {"ceiling", "floor", "wall", "walls", "floor material"}
    fixed_str = ", ".join(f for f in fixed_elements if f.lower() not in skip_generic)

    prompt = f"""Role: Expert Virtual Stager.
Task: Furnish the empty space in the image with perfect consistency and spatial awareness.
Style: {style}.

╔══════════════════════════════════════════════════════════════╗
║          ARCHITECTURAL CONSTRAINTS - ABSOLUTE RULES          ║
╚══════════════════════════════════════════════════════════════╝

YOU ARE FORBIDDEN FROM MODIFYING THE ROOM'S STRUCTURE.
THIS IS VIRTUAL STAGING, NOT RENOVATION.

PROHIBITED (IMMEDIATE REJECTION):
❌ WALLS: Do NOT add, remove, move, or modify walls
❌ FLOORS: Do NOT change flooring materials, patterns, or add transitions
❌ CEILINGS: Do NOT add/remove ceiling elements or change lighting fixtures
❌ WINDOWS: Do NOT add, resize, move, or block windows
❌ DOORS: Do NOT add, move, or block doors or doorways
❌ BUILT-INS: Do NOT add islands, counters, cabinets, shelving, or built-in furniture
❌ UTILITIES: Do NOT add plumbing fixtures, electrical outlets, or HVAC elements

ALLOWED STAGING ITEMS:
✅ MOVABLE FURNITURE: Sofas, tables, chairs, beds, dressers
✅ LIGHTING: Floor lamps, table lamps (plugged in, not built-in)
✅ DECOR: Artwork, plants, books, vases, decorative objects
✅ TEXTILES: Rugs, curtains, pillows, throws

SIMPLE TEST: If you cannot physically carry it through the door in pieces, DO NOT ADD IT.
"""

    if spatial_layout:
        prompt += """
╔══════════════════════════════════════════════════════════════╗
║          SPATIAL LAYOUT (MUST FOLLOW)                        ║
╚══════════════════════════════════════════════════════════════╝

The following spatial relationships MUST be preserved:

"""
        for rel in spatial_layout:
            prompt += f"- {rel.get('subject', '')} {rel.get('relation', '')} {rel.get('object', '')}\n"
        prompt += "\nThese spatial relationships are MANDATORY and cannot be altered."

    if cannot_block:
        names = [item["element_name"] for item in cannot_block]
        prompt += f"""

╔══════════════════════════════════════════════════════════════╗
║     🚨 STRICT NEGATIVE CONSTRAINTS — FORBIDDEN 🚨           ║
╚══════════════════════════════════════════════════════════════╝

The following elements MUST remain fully visible and intact:
{", ".join(names)}

ABSOLUTE PROHIBITIONS:
1. DO NOT remove these elements from the image
2. DO NOT hide these elements behind furniture
3. DO NOT erase these elements to make room for staging
4. Furniture placement MUST work around these elements

If the room feels tight, REDUCE FURNITURE QUANTITY.
PRIORITY: Preserve these elements > Add furniture
"""

    if can_place_on_top:
        surface_names = [item["element_name"] for item in can_place_on_top]
        prompt += f"""

╔══════════════════════════════════════════════════════════════╗
║          SURFACES THAT MAY HOLD ITEMS                        ║
╚══════════════════════════════════════════════════════════════╝

These surfaces are available for small decorative items:
{", ".join(surface_names)}

You may place items like vases, books, fruit bowls on these surfaces.
"""

    if not cannot_block and not can_place_on_top and fixed_str:
        prompt += f"\nPROTECTED FIXTURES (DO NOT COVER OR OBSTRUCT):\n{fixed_str}\n"

    prompt += f"""

*** CRITICAL ZONING HIERARCHY (MANDATORY) ***
PRIMARY ZONE (FOREGROUND): {room_type}
- ONLY use {room_type}-appropriate furniture in the FOREGROUND
- DO NOT place secondary zone furniture in the primary zone
"""

    if visible_zones:
        prompt += "\nSECONDARY ZONES (BACKGROUND ONLY):\n"
        for i, zone in enumerate(visible_zones):
            prompt += f"{i+1}. {zone}\n"
            prompt += f"   - ONLY add {zone} furniture if clearly visible in DEEP background\n"
            prompt += f"   - Keep {zone} staging MINIMAL and SUBTLE\n"

    if inventory:
        prompt += f"""

### 📋 ROOM INVENTORY - FURNITURE THAT EXISTS ###
This is a different camera angle of the SAME ROOM photographed earlier.
The inventory below lists furniture that EXISTS in this room with their positions.

{inventory}

*** CRITICAL CAMERA ANGLE RULES (MANDATORY) ***
1. PARTIAL VISIBILITY IS ACCEPTABLE — furniture at frame edges may be cut off
2. RESPECT CAMERA PERSPECTIVE — only show furniture naturally visible from this angle
3. FRAME BOUNDARIES ARE ABSOLUTE — do not crowd furniture to fit everything in frame
4. DOOR/WINDOW PROTECTION OVERRIDES INVENTORY — never block doors/windows for furniture
5. MAINTAIN STYLE CONSISTENCY — match exact style, color, material from inventory

PRIORITIZATION ORDER:
1st: Preserve doors/windows (NEVER block)
2nd: Respect camera frame (partial/omitted items OK)
3rd: Show inventory items (only if naturally visible from this angle)
"""
    elif layout_instructions:
        prompt += """

╔══════════════════════════════════════════════════════════════╗
║          STYLE LAYOUT RULES                                  ║
╚══════════════════════════════════════════════════════════════╝

"""
        prompt += "\n".join(f"- {rule}" for rule in layout_instructions)

    if custom_instructions:
        prompt += f"\n\nADDITIONAL NOTES FROM USER: {custom_instructions}"

    # SINGLE IMAGE INPUT ONLY — prevents collage hallucinations
    response = client.models.generate_content(
        model=PAINTER_MODEL,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            temperature=0.4,
        ),
    )

    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return part.inline_data.data

    raise RuntimeError("Painter returned no image. Check Gemini quota or model availability.")


def extract_inventory(client: genai.Client, staged_bytes: bytes, room_type: str, visible_zones: list) -> str:
    """Extract zone-segmented furniture inventory from the staged image for multi-angle consistency."""
    print("  [Inventory] Extracting furniture catalog for multi-angle consistency...")
    zones_text = room_type
    if visible_zones:
        zones_text += f" and {', '.join(visible_zones)}"

    prompt = f"""Analyze this staged interior image containing: {zones_text}.
Create a furniture inventory to ensure consistency in future camera angles.

RULES:
1. Group items by [ZONE] headers using uppercase zone names.
2. For each item: list Style, Color, Material.
3. CRITICAL: Describe GEOMETRIC ALIGNMENT relative to walls/windows (e.g., "Parallel to back wall", "Perpendicular to window").
4. CRITICAL: Do NOT list architectural features (islands, cabinets, built-ins). ONLY movable furniture and decor.

Format:
[{room_type.upper()} ZONE]
- Item Name (Color, Material) - Positioned <location>, aligned <geometric alignment>

Focus on visual descriptions that define the style and must remain consistent across camera angles.
"""
    response = client.models.generate_content(
        model=ARCHITECT_MODEL,
        contents=[prompt, types.Part.from_bytes(data=staged_bytes, mime_type="image/png")],
    )
    inventory = response.text.strip()
    print(f"  [Inventory] Extracted {len(inventory)} chars")
    return inventory


def save_session(session_dir: Path, analysis: dict, inventory: str, staged_bytes: bytes) -> None:
    """Persist anchor data so subsequent angles can maintain consistency."""
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "anchor_analysis.json").write_text(json.dumps(analysis, indent=2))
    (session_dir / "inventory.txt").write_text(inventory)
    (session_dir / "anchor.png").write_bytes(staged_bytes)


def load_session(session_dir: Path) -> tuple[dict, str]:
    """Load anchor analysis and inventory from a prior session."""
    analysis_path = session_dir / "anchor_analysis.json"
    inventory_path = session_dir / "inventory.txt"
    if not analysis_path.exists() or not inventory_path.exists():
        raise FileNotFoundError(
            f"Session data not found in {session_dir}. "
            "Run the first angle without --session-dir to create a session."
        )
    analysis = json.loads(analysis_path.read_text())
    inventory = inventory_path.read_text()
    return analysis, inventory


def main():
    parser = argparse.ArgumentParser(
        description="Virtually stage an empty room photo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First angle (creates session)
  python generate_staging.py room.jpg "Modern" --output staged.png

  # Second angle (reuses session for consistency)
  python generate_staging.py room_angle2.jpg "Modern" --session-dir ./staging_sessions/abc-123 --output staged2.png

  # With custom instructions
  python generate_staging.py room.jpg "Scandinavian" --room-type "Bedroom" --custom "Add a reading chair" --output bedroom.png
""",
    )
    parser.add_argument("image", help="Path to empty room photo (JPG, PNG, WEBP)")
    parser.add_argument("style", help="Design style: Modern, Scandinavian, Industrial, Boho Chic, Minimalist, Mediterranean, Art Deco")
    parser.add_argument("--room-type", help="Room type (auto-detected if omitted)")
    parser.add_argument("--session-dir", help="Session directory from a prior run (for multi-angle consistency)")
    parser.add_argument("--output", default="staged_output.png", help="Output file path (default: staged_output.png)")
    parser.add_argument("--custom", help="Custom staging instructions")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        print("Set it with: export GOOGLE_API_KEY=your_key_here")
        sys.exit(1)

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    image_bytes = image_path.read_bytes()
    mime = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    # Normalize to jpeg bytes for consistent handling
    _ = mime  # used in architect_analyze via hardcoded jpeg below

    is_multi_angle = args.session_dir is not None
    session_dir = Path(args.session_dir) if args.session_dir else Path("./staging_sessions") / str(uuid.uuid4())[:8]

    print(f"\nStaging: {image_path.name} | Style: {args.style}{' | Multi-angle' if is_multi_angle else ''}")
    print("─" * 60)

    try:
        # --- Phase 1: Architect ---
        if is_multi_angle:
            print("[1/3] Loading anchor session for multi-angle consistency...")
            _, inventory = load_session(session_dir)
            # Analyze current angle for its own spatial constraints
            analysis = architect_analyze(client, image_bytes, args.room_type)
        else:
            inventory = None
            analysis = architect_analyze(client, image_bytes, args.room_type)

        room_type = analysis.get("room_type", args.room_type or "Room")
        visible_zones = analysis.get("visible_zones", [])

        # --- Style lookup ---
        print("[2/3] Looking up style layout rules...")
        layout_instructions = get_style_instructions(args.style, room_type, visible_zones)

        # --- Phase 2: Painter ---
        print("[3/3] Generating staged image...")
        staged_bytes = painter_stage(
            client=client,
            image_bytes=image_bytes,
            style=args.style,
            analysis=analysis,
            layout_instructions=layout_instructions,
            inventory=inventory if is_multi_angle else None,
            custom_instructions=args.custom,
        )

        # --- Save output ---
        output_path = Path(args.output)
        output_path.write_bytes(staged_bytes)

        # --- Session management (anchor only) ---
        if not is_multi_angle:
            print("[Session] Extracting furniture inventory for future angles...")
            inventory = extract_inventory(client, staged_bytes, room_type, visible_zones)
            save_session(session_dir, analysis, inventory, staged_bytes)

        print("─" * 60)
        print(f"Room: {room_type} | Style: {_resolve_style(args.style)}")
        if visible_zones:
            print(f"Visible zones: {', '.join(visible_zones)}")
        if not is_multi_angle:
            print(f"Session directory: {session_dir.resolve()}")
        print(f"Output: {output_path.resolve()}")
        print("Done.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
