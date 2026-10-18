"""Reproduce the explicitly fictional UI used by renderer smoke tests."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    root = Path(__file__).resolve().parents[1]
    font_file = root / 'assets/fonts/manrope.ttf'
    image = Image.new('RGB', (1200, 675), '#eceee5')
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(str(font_file), 25)
    heading = ImageFont.truetype(str(font_file), 38)
    small = ImageFont.truetype(str(font_file), 19)
    draw.rounded_rectangle((28, 28, 1172, 647), 20, fill='#ffffff', outline='#d1d7ca', width=2)
    draw.rounded_rectangle((28, 28, 1172, 104), 20, fill='#233d33')
    draw.rectangle((28, 72, 1172, 104), fill='#233d33')
    draw.text((60, 47), 'DEMO WORKSPACE  /  FICTIONAL INTERFACE', font=regular, fill='#f3f8f2')
    draw.text((66, 145), 'A plan the whole team can follow', font=heading, fill='#1b3328')
    for x, title, lines in [
        (66, 'Plan', ['Define the goal', 'Choose a direction', 'Prepare a review']),
        (434, 'Review queue', ['New concept', 'Source check', 'Ready to discuss']),
        (802, 'Decisions', ['Keep the evidence', 'Record the choice', 'Share the next step']),
    ]:
        draw.rounded_rectangle((x, 233, x + 330, 553), 12, fill='#f2f5ed')
        draw.text((x + 24, 260), title, font=regular, fill='#1b3328')
        for index, line in enumerate(lines):
            y = 327 + index * 61
            draw.ellipse((x + 25, y + 5, x + 39, y + 19), fill='#578a63')
            draw.text((x + 52, y), line, font=small, fill='#395844')
    draw.text((68, 590), 'Synthetic illustration for layout tests. No real product or customer data.', font=small, fill='#556a5c')
    image.save(root / 'tests/fixtures/product-interface.png')


if __name__ == '__main__':
    main()
