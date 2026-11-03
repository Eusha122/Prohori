"""Build the Prohori logo ("Data Rise": three rising bars + a red watch point) as SVG files.

Writes:
  prohori-icon.svg        main mark, transparent background (for white pages)
  prohori-icon-plain.svg  white variant for green bands / dark backgrounds
  prohori-icon-tile.svg   mark on a white rounded square (phone home-screen icons)
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent
LIGHT, MID, DARK = "#8cca5e", "#4f9a2c", "#2c6e1c"
RED = "#d62828"


def mark(c1: str, c2: str, c3: str, base: str, base_opacity: float,
         bar_opacity=(1, 1, 1)) -> str:
    """The logo drawn in a 64x64 box."""
    o1, o2, o3 = bar_opacity
    return (
        f'<rect x="11" y="34" width="11" height="22" rx="3" fill="{c1}" opacity="{o1}"/>'
        f'<rect x="26.5" y="24" width="11" height="32" rx="3" fill="{c2}" opacity="{o2}"/>'
        f'<rect x="42" y="14" width="11" height="42" rx="3" fill="{c3}" opacity="{o3}"/>'
        f'<circle cx="47.5" cy="6.5" r="4.4" fill="{RED}"/>'
        f'<rect x="8" y="58" width="48" height="3" rx="1.5" fill="{base}" opacity="{base_opacity}"/>'
    )


def write(name: str, body: str):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="512" height="512">'
           f'<title>Prohori</title>{body}</svg>\n')
    (OUT / name).write_text(svg, encoding="utf8")
    print("wrote", OUT / name)


def main():
    write("prohori-icon.svg", mark(LIGHT, MID, DARK, DARK, 0.35))
    write("prohori-icon-plain.svg",
          mark("#ffffff", "#ffffff", "#ffffff", "#ffffff", 0.45, bar_opacity=(0.6, 0.8, 1)))
    # Tile: shrink the mark into a white rounded square with a little margin.
    write("prohori-icon-tile.svg",
          '<rect x="0" y="0" width="64" height="64" rx="14" fill="#ffffff"/>'
          f'<g transform="translate(8 8) scale(0.75)">{mark(LIGHT, MID, DARK, DARK, 0.35)}</g>')


if __name__ == "__main__":
    main()
