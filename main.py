import fontforge
import svgwrite
import math
import numpy as np
import cairosvg
from PIL import Image
import potrace
from pathlib import Path

root_output_dir = "outputs"
svg_working_file = f"{root_output_dir}/temp.svg"
png_working_file = f"{root_output_dir}/temp.png"
regen_svgs = True
version = "0.1"

# should probably parameterize these
height = 200
stroke_width = 4.5


def createCharFromSvg(font, char, filename, translation_factor, force_scale=None):
    fontChar = font.createChar(ord(char))
    fontChar.importOutlines(filename)
    box = fontChar.boundingBox()
    original_height = box[3] - box[1]
    original_width = box[2] - box[0]
    scale = (original_width / original_height) if force_scale is None else force_scale
    width = font.em * scale
    if scale > 1:
        transformation_matrix = (scale, 0, 0, scale, -4, translation_factor)
        fontChar.transform(transformation_matrix)
    elif force_scale is not None:
        width = min(original_width, width)
        print(width)
    # - 4 to ensure a little overlap with previous
    fontChar.width = math.ceil(width) - 4
    return scale


# adapted from: https://github.com/tatarize/potrace/pull/8/files
def path_to_svg(width, height, path, output_file):
    with open(output_file, "w") as fp:
        fp.write(
            f'<svg version="1.1"'
            + f' xmlns="http://www.w3.org/2000/svg"'
            + f' xmlns:xlink="http://www.w3.org/1999/xlink"'
            + f' width="{width}" height="{height}"'
            + f' viewBox="0 0 {width} {height}">'
        )
        parts = []
        for curve in path:
            fs = curve.start_point
            parts.append("M%f,%f" % (fs.x, fs.y))
            for segment in curve.segments:
                if segment.is_corner:
                    a = segment.c
                    parts.append("L%f,%f" % (a.x, a.y))
                    b = segment.end_point
                    parts.append("L%f,%f" % (b.x, b.y))
                else:
                    a = segment.c1
                    b = segment.c2
                    c = segment.end_point
                    parts.append("C%f,%f %f,%f %f,%f" % (a.x, a.y, b.x, b.y, c.x, c.y))
            parts.append("z")
        fp.write(
            f'<path stroke="none" fill="#000" fill-rule="evenodd" d="{"".join(parts)}"/>'
        )
        fp.write("</svg>")


def svg_for_code(
    number: int,
    output_dir: str,
    samples_per_bit: int,
    noise_amount: float,
    start_bit: bool,
    end_bit: bool,
):
    output_path = f"{output_dir}/{str(number)}.svg"
    if not regen_svgs:
        return output_path
    binary_number = format(number, "08b")
    if start_bit:
        binary_number = "0" + binary_number
    if end_bit:
        binary_number = binary_number + "1"
    # invert signal
    binary_signal = np.array([-1 if bool(int(bit)) else 1 for bit in binary_number])
    signal = np.repeat(binary_signal, samples_per_bit)
    expanded_time = np.linspace(0, len(binary_number), len(signal))
    noise = np.random.normal(0, noise_amount, expanded_time.shape)
    signal = signal + noise

    scale = height * (0.95 - noise_amount)
    pos = (3, -scale)
    samples = len(signal)
    # add some padding at the end to make room for the falling edge
    if end_bit:
        samples += 4

    dwg = svgwrite.Drawing(
        svg_working_file,
        profile="tiny",
        size=(f"{samples}mm", f"{2*height}mm"),
        viewBox=(f"0 {-height} {samples} {2*height}"),
    )

    for p in signal:
        (prev_x, prev_y) = pos
        y_delt = prev_y - (p * scale)
        x = prev_x + 1
        dwg.add(
            dwg.line(
                pos,
                (x, prev_y - y_delt),
                stroke=svgwrite.rgb(0, 0, 0),
                stroke_width=stroke_width,
            )
        )
        pos = (x, prev_y - y_delt)
    if end_bit:
        dwg.add(
            dwg.line(
                pos,
                (prev_x + 2, prev_y),
                stroke=svgwrite.rgb(0, 0, 0),
                stroke_width=stroke_width,
            )
        )

    # You're gonna read this and think: "is he really going from svg -> png -> back to svg?"
    # Yes, I am! The potrace result looks more "organic", simplifies the final svg,
    # and allows me to write more simple svg generation code up front.
    dwg.save(pretty=True)
    cairosvg.svg2png(
        url=svg_working_file,
        write_to=png_working_file,
        scale=0.3,
        background_color="#FFF",
    )
    image = Image.open(png_working_file).convert("L")
    bitmap = potrace.Bitmap(np.array(image))
    path = bitmap.trace(opttolerance=0.8)
    path_to_svg(image.width, image.height, path, output_path)
    return output_path


def create_font(weight, samples_per_bit, noise_amount):
    print(f"CREATE VARIANT: {weight}")
    svg_dir = f"{root_output_dir}/{weight}"
    Path(svg_dir).mkdir(parents=True, exist_ok=True)

    font = fontforge.font()
    font.encoding = "UnicodeFull"
    font.version = version
    font.weight = weight
    font.fontname = f"ScopinSans-{weight}"
    font.familyname = "ScopinSans"
    font.fullname = f"ScopinSans-{weight}"
    font.em = 512
    max_scale = 0
    # This is not real math, these values just made it work for now.
    y_adjustment = -((10 * samples_per_bit) - (360 + (noise_amount * 500)))

    for code in range(0, 128):
        print(code)
        svg_path = svg_for_code(
            number=code,
            output_dir=svg_dir,
            samples_per_bit=samples_per_bit,
            noise_amount=noise_amount,
            start_bit=True,
            end_bit=True,
        )

        current_scale = createCharFromSvg(font, chr(code), svg_path, y_adjustment)
        if current_scale > max_scale:
            max_scale = current_scale

    # choose some values to hold variations of "signal high"
    # handy if you wanna space out words
    for c in ["¡", "£", "¢"]:
        svg_path = svg_for_code(
            number=0b11111111,
            output_dir=svg_dir,
            samples_per_bit=samples_per_bit,
            noise_amount=noise_amount,
            start_bit=False,
            end_bit=False,
        )
        # use scale value from previously generated characters to make sure they match
        createCharFromSvg(font, c, svg_path, y_adjustment, force_scale=max_scale)

    font_dir = f"{root_output_dir}/ScopinSans"
    Path(font_dir).mkdir(parents=True, exist_ok=True)
    font.generate(f"{font_dir}/ScopinSans-{weight}.ttf")
    font.generate(f"{font_dir}/ScopinSans-{weight}.woff2")
    font.close()


create_font("NoNoise", samples_per_bit=80, noise_amount=0.0)
create_font("Regular", samples_per_bit=100, noise_amount=0.04)
create_font("FastBaud", samples_per_bit=30, noise_amount=0.04)
