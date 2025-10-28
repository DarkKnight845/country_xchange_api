import os

from PIL import Image, ImageDraw, ImageFont

from src.config import Config


def generate_summary_image(total_count, top_5_countries, timestamp):
    """Generates and saves the cache/summary.png image."""

    # Ensure cache directory exists
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    image_path = os.path.join(Config.CACHE_DIR, "summary.png")

    # Simple image generation using Pillow
    img = Image.new("RGB", (600, 400), color=(30, 30, 70))
    d = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_mono = ImageFont.truetype("cour.ttf", 14)
    except IOError:
        # Fallback if system fonts aren't found
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    d.text((20, 20), "🌐 API Cache Summary", fill=(255, 200, 0), font=font_large)

    d.text(
        (20, 60),
        f"Total Countries Cached: {total_count}",
        fill=(200, 200, 255),
        font=font_small,
    )
    d.text(
        (20, 85),
        "Last Successful Refresh (UTC):",
        fill=(200, 200, 255),
        font=font_small,
    )
    d.text(
        (30, 110),
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S Z')}",
        fill=(100, 255, 100),
        font=font_mono,
    )

    # Top 5 GDP List
    y_pos = 150
    d.text((20, y_pos), "Top 5 Estimated GDP:", fill=(255, 255, 255), font=font_small)
    y_pos += 25

    for i, country in enumerate(top_5_countries):
        gdp_val = country.estimated_gdp
        gdp_str = f"${float(gdp_val):,.2f}" if gdp_val is not None else "N/A"

        line = f"{i + 1}. {country.name.ljust(25)} {gdp_str}"
        d.text((30, y_pos), line, fill=(255, 255, 255), font=font_mono)
        y_pos += 20

    img.save(image_path)
