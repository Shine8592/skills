# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "pillow>=10.0.0", "qrcode>=7.0"]
# ///
"""Generate a single Sundial trading card (front and/or back) from direct CLI args."""

import argparse
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import qrcode
from google import genai
from google.genai import types
from PIL import Image as PILImage

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_FRONT = SKILL_DIR / "templates" / "reference-front.jpg"
TEMPLATE_BACK = SKILL_DIR / "templates" / "reference-back.png"

RARITY_PALETTE = {
    "Legendary": "rich radiant gold, warm glowing amber, luxurious golden highlights — the most prestigious tier, luminous and special",
    "Epic": "warm bronze and copper tones — rich and warm but more orange-bronze than pure gold, amber-copper accents instead of bright gold",
    "Rare": "muted warm tones — earthy amber-brown, less saturated, subtle warmth, aged parchment and warm sepia rather than bright gold",
    "Common": "dark brown and muted earth tones — worn leather, dark coffee brown, desaturated sepia, no gold glow, deep warm browns and dark umber, rugged and humble",
}

FRONT_PROMPT = """\
Edit this trading card to create a new card for a different skill. Keep the EXACT same card frame, layout, square corners, and structure, and PORTRAIT orientation (taller than wide). The color palette should be {palette}.

CARD FRAME RULES (do NOT change these elements from the reference):
- TOP-LEFT: Keep the exact same sun/sundial logo. Do NOT replace it with an emoji, text, or author name.
- TOP-RIGHT: Keep the download count number with the download arrow icon. Do NOT replace the download icon with any other symbol.
- TITLE BANNER: Show ONLY the skill name text in the banner. No emoji in the title.
- BOTTOM: "by author" text at the very bottom.

TITLE: {name}
AUTHOR: {author}
DOWNLOADS: {downloads}

CHARACTER: Replace the character illustration with {character}

DESCRIPTION/POWERS at the bottom ({powers_label}):
{powers_block}

Keep everything else identical: card border, text styling, layout positions, square corners, portrait orientation. Must look like same card set."""

BACK_PROMPT = """\
Generate the BACK side of this trading card. Match the exact same golden/amber warm color palette, ornate border style, and overall aesthetic. Same square corners, portrait orientation (taller than wide).

BACK DESIGN REQUIREMENTS:
- BORDER: Same ornate golden/amber border frame as the reference
- TOP: The Sundial sun/sundial logo centered and larger
- CENTER: A large QR code in the middle surrounded by an ornate golden frame. The QR code should link to {url}. It should look like a real scannable black-and-white square grid pattern.
- BELOW QR: The text "sundialhub.com" in elegant golden lettering
- BOTTOM: Small text "Scan to explore this skill"
- BACKGROUND: Rich warm golden/amber gradient with subtle ornate filigree decorations
- Overall feel: premium, collectible, magical — like the back of a Pokemon or MTG card but in the Sundial golden theme

The color warmth should reflect the rarity: {palette}.

Do NOT include any character illustration. This is purely the card back with branding and QR code.
Keep PORTRAIT orientation and same dimensions as the reference."""


def load_reference(path: Path) -> PILImage.Image:
    img = PILImage.open(path)
    img.load()
    return img


def generate_front(args, client: genai.Client) -> str:
    ref_img = load_reference(Path(args.reference_front) if args.reference_front else TEMPLATE_FRONT)
    palette = RARITY_PALETTE[args.rarity]
    n_powers = len(args.powers)
    powers_label = f"only {n_powers} powers, not three" if n_powers == 2 else f"{n_powers} powers"
    powers_block = "\n".join(f"- {p}" for p in args.powers)

    prompt = FRONT_PROMPT.format(
        palette=palette, name=args.name, author=args.author,
        downloads=args.downloads, character=args.character,
        powers_label=powers_label, powers_block=powers_block,
    )

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[ref_img, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(image_size=args.resolution),
        ),
    )

    slug = args.name.lower().replace(" ", "-").replace("/", "-")
    fname = f"{slug}-{args.rarity.lower()}.png"
    return _save_image(response, Path(args.output_dir) / fname)


def generate_back(args, client: genai.Client) -> str:
    ref_img = load_reference(Path(args.reference_back) if args.reference_back else TEMPLATE_BACK)
    palette = RARITY_PALETTE[args.rarity]
    url = args.url or f"https://sundialhub.com/{args.slug}"

    prompt = BACK_PROMPT.format(palette=palette, url=url)

    contents: list = [ref_img]
    if args.qr_url:
        qr_img = _make_qr_image(args.qr_url)
        contents.append(qr_img)
        prompt += "\n\nIMPORTANT: The second image provided is a real, scannable QR code. You MUST use this EXACT QR code pixel-perfectly in the center of the card — do NOT generate or invent your own QR pattern. Copy this QR code exactly as-is into the card design."
    contents.append(prompt)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(image_size=args.resolution),
        ),
    )

    slug = args.name.lower().replace(" ", "-").replace("/", "-")
    fname = f"{slug}-{args.rarity.lower()}-back.png"
    return _save_image(response, Path(args.output_dir) / fname)


def _make_qr_image(url: str) -> PILImage.Image:
    """Generate a real scannable QR code as a PIL image."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _save_image(response, out_path: Path) -> str:
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            img = PILImage.open(BytesIO(part.inline_data.data))
            img.save(out_path)
            print(f"  -> {out_path.name}  ({img.size[0]}x{img.size[1]})")
            return out_path.name
    print("  x no image in response")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Generate a single Sundial trading card")
    parser.add_argument("--name", required=True, help="Skill display name")
    parser.add_argument("--author", required=True, help="Skill author")
    parser.add_argument("--downloads", default="0", help="Download count (default: 0)")
    parser.add_argument("--rarity", default="Common", choices=["Common", "Rare", "Epic", "Legendary"])
    parser.add_argument("--slug", required=True, help="Skill slug (author/skill-name)")
    parser.add_argument("--url", default=None, help="Skill URL (default: https://sundialhub.com/{slug})")
    parser.add_argument("--character", required=True, help="Character illustration description")
    parser.add_argument(
        "--powers",
        required=True,
        nargs="+",
        action="append",
        help='Repeatable. Powers, each like: "emoji **Title** -- Description"',
    )
    parser.add_argument("--side", choices=["front", "back", "both"], default="both")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--reference-front", default=None, help="Override front template")
    parser.add_argument("--reference-back", default=None, help="Override back template")
    parser.add_argument("--api-key", default=None, help="Gemini API key (or GEMINI_API_KEY env)")
    parser.add_argument("--qr-url", default=None, help="URL to encode as a real scannable QR code on back cards")
    parser.add_argument("--resolution", default="2K", help="Image resolution (default: 2K)")
    args = parser.parse_args()

    args.powers = [power.strip() for group in args.powers for power in group if power and power.strip()]
    if len(args.powers) < 2 or len(args.powers) > 3:
        print("Error: provide 2 or 3 powers total (repeat --powers for each power).", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: provide --api-key or set GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    do_front = args.side in ("front", "both")
    do_back = args.side in ("back", "both")

    start = time.time()
    ok, fail = 0, 0

    if do_front:
        print(f"Generating front: {args.name} ({args.rarity})")
        try:
            if generate_front(args, client):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  x FRONT ERROR: {e}")
            fail += 1

    if do_back:
        print(f"Generating back: {args.name} ({args.rarity})")
        try:
            if generate_back(args, client):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  x BACK ERROR: {e}")
            fail += 1

    print(f"\nDone in {time.time() - start:.0f}s — {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
