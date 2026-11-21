import io
from PIL import Image, ImageDraw

SET_COLORS = {
    "Speed": (0, 210, 211),
    "Offense": (235, 77, 75),
    "Critical Damage": (240, 147, 43),
    "Critical Chance": (104, 109, 229),
    "Health": (106, 176, 76),
    "Defense": (126, 214, 223),
    "Potency": (190, 46, 221),
    "Tenacity": (48, 51, 107),
}


def build_mod_set_image(character: str, sets: list[tuple[str, int]], primaries: list[str]) -> io.BytesIO:
    width, height = 900, 340
    img = Image.new("RGB", (width, height), (24, 27, 36))
    draw = ImageDraw.Draw(img)

    draw.rectangle([20, 20, width - 20, height - 20], outline=(68, 76, 102), width=2)
    draw.text((45, 38), f"TOP MODS SET: {character.upper()}", fill=(255, 255, 255))

    x = 45
    y = 90
    for set_name, count in sets:
        color = SET_COLORS.get(set_name, (120, 144, 156))
        draw.rounded_rectangle([x, y, x + 250, y + 85], radius=12, fill=(36, 41, 54), outline=color, width=3)
        draw.ellipse([x + 15, y + 20, x + 60, y + 65], fill=color)
        draw.text((x + 75, y + 20), f"{set_name} x{count}", fill=(255, 255, 255))
        draw.text((x + 75, y + 45), "Recommended set", fill=(180, 190, 210))
        x += 275

    draw.text((45, 205), "Key stats / primaries:", fill=(200, 210, 230))
    draw.text((45, 235), " | ".join(primaries), fill=(255, 215, 100))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf