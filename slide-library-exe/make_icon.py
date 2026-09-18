"""Regenerates icon.ico (the brand "S" mark). Only needed if the design changes: `python make_icon.py`."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=56, fill="#2B3A55")
font = ImageFont.load_default(size=170)
d.text((SIZE / 2, SIZE / 2 + 6), "S", fill="white", font=font, anchor="mm")
img.save(Path(__file__).with_name("icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
