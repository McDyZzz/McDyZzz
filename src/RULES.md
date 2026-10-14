# Profile rules

`README.md` renders the GitHub profile of McDyZzz. Every image in `assets/` comes from `src/`, except `assets/header.svg`.

## Rebuild

```sh
cd src
./build.sh            # regenerate assets/ (python3 only)
./build.sh --check    # also build the preview (src/index.html) and run check.mjs
```

`--check` needs the `gh` CLI signed in, Node 22+, Google Chrome and xmllint. The comparison shots against official SETI art run only when `src/local/seti-ref/` exists. `src/local/` is gitignored.

1. AI or HUMAN edits a generator in `src/gen/`, never a generated SVG.
2. AI or HUMAN runs `./build.sh --check` and opens `src/index.html` before every commit.
3. Commits are authored as McDyZzz.

## Hard rules

- **Personal info:** the name McDyZzz is the only personal detail in this repo. No real name, location, employer or email.
- **SVG:** self-contained, with no script, no foreignObject, no external URLs or fonts, and no event handlers. All text is drawn as path outlines. Every file passes `xmllint --noout`. Every animated file has a `prefers-reduced-motion: reduce` rule that stops all motion.
- **Fonts:** open licence only. The files and their OFL texts live in `src/fonts/`.
- **SETI art:** official SETI art is never traced or embedded. Scenes and shapes are drawn in code. The resource icons (credit, energy, move, signals) are vector outlines in `src/gen/icons/seti_icons.json`, traced from the v1 sprite sheet of the fan site seti.ender-wiggin.com. The raw sheet stays in `src/local/` and is not committed.
- **Paths:** every path in `src/` is relative.

## Page order

1. Header
2. About heading, About text
3. Featured projects heading, project cards
4. Footer
5. Easter egg (collapsed `<details>`)

## Theme and width switching

Each themed image is a `<picture>`. The browser takes the first matching source:

```html
<picture>
  <source media="(max-width: 1011px) and (prefers-color-scheme: dark)" srcset="assets/X-phone-dark.svg">
  <source media="(max-width: 1011px)" srcset="assets/X-phone-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/X-dark.svg">
  <img src="assets/X-light.svg" alt="...">
</picture>
```

- Phone layout: window width 1011 px or less. At 375 px the README content is 293 px wide.
- Desktop layout: at 1280 px the README content is 846 px wide.
- Images carry no width attribute, so each one shows at its SVG's own size, capped at the content width.

## Type

| Role | Font | Where |
|---|---|---|
| Display | Oxanium (OFL) | Repo names on cards, section headings |
| Body | Jost (OFL) | About, card text, easter egg |
| Pixel 5×7 | Drawn in code (`gen/tools/pixelfont.py`) | Header typing line only |

## Header

- `assets/header.svg` is hand-maintained. No generator writes it.
- The typing line cycles through quotes. No background star sits inside the area the longest quote and its cursor cover.
- `gen/footer/build.py` reads the header, so a header edit changes the footer on the next build.
- The alt text of the header describes the earlier game-board art and needs updating when the header changes.

## About

- Text source: `src/gen/about/about.md`. The README alt text repeats it.
- Transparent background with no box, so the text sits on the page colour.
- Jost 430. **BUT** is uppercase, Jost 680, amber: #9a6700 in light, brighter amber in dark.
- Desktop: two columns (items 1–3 and 4–6), about 15 px. Phone: one column, about 14 px.
- No line holds a single word.

## Section headings

- Tag shape with the signal icon, text in Oxanium SemiBold 600, uppercase, letter spacing 0.11 em.
- Light: fill #f6f8fa, border #d1d9e0. Dark: fill #161b22, border #30363d.
- Plain paragraphs, so GitHub adds no anchor link icon.
- The tag's left edge lines up with the header.

## Project cards

Desktop row: two cards plus the card back (a draw pile) in three slots, outer edges lined up with the header. The card back shows only at window width 1280 px and up. Below that, `blank.svg` (0×0) fills the slot. Phone: wide short cards, one per row.

Card front, top to bottom:

1. **Art (top part):** a dimensional illustration with depth, light and calm looping animation.
2. **Top-left corner:** a dark diagonal triangle (#141924) with the white radio-dish icon and a small orange planet.
3. **Top-right corner:** a sector-colour triangle with the white signal icon. Its bars pulse.
4. **Title band:** a full-width band in the sector colour. A gold diamond (#e1ab31) holds the project icon and overlaps the band's left end. The repo name is lowercase, Oxanium Bold 700, pure white, at least 18 px, about 11 px right of the diamond tip, with at least 7 px margin at the band's right end.
5. **Effect panel:** a pale panel (dark panel in dark theme) with the one-line description in Jost and the effect icons. Icons sit in plain white circles.
   - 1 icon: left of the text.
   - 2 icons: above the text.
   - 3 icons: below the text.
6. **Bottom:** the italic line "Claude Code plugin", the rotated card code at the far left, and the income corner (a trapezoid plus a strip along the bottom edge) at the bottom right.

Icons, badges, corners and panels are flat: no bevels, gradients or shadows. Only the art has depth. Device and chart icons are mirror-symmetric, and `check.mjs` tests this.

| | idevice-control | cc-session-breakdown |
|---|---|---|
| Sector colour | blue #3578d8 | red #e0442a |
| Diamond icon | phone | pie |
| Line | Lets Claude use a real iPhone, iPad or Apple TV. | Shows where your Claude Code usage went. |
| Effect icons | iPhone, iPad, TV (below the text) | pie chart (left of the text) |
| Income corner | energy, green | credit, gold |
| Card code | MZ EN 01 | MZ EN 02 |
| Link | github.com/McDyZzz/idevice-control | github.com/McDyZzz/cc-session-breakdown |

Minimum rendered text sizes: desktop line 14 px, phone 11 px. The flavour line and card code are decorative and exempt.

## Card back

- A 1950s travel-poster scene: flat faces in two tones, no outlines, no gradients inside the scene, paper grain and a vignette. The palette lives in `gen/back/build_back.py`.
- Motif: an orange-red radio dish with a cream bowl, a crescent moon in a teal sky, a rocket trail, clouds, and an ochre desert with a road.
- Frame: off-white #f4f2ee.
- Pile: a stack of off-white cards, seen from above and slightly in front, with light from the upper right. The front and left side faces show fine card-edge lines and are darker than the top. A few cards are slightly misaligned, and the pile casts a soft shadow that is stronger on dark pages.
- Motion: the rocket climbs, clouds drift, the dish nods, stars twinkle.

## Easter egg

The summary and the revealed lines are Jost images inside `<details>`, so they match the About text:

```
Don't click this.

I taught Claude to tap my iPhone.
Then it wanted the Apple TV remote.
Now it reads my token bills.
```

## Footer

The Sun and the eight planets in one flat row, with an asteroid belt and a comet, and no text. `gen/footer/build.py` builds it from parts of the header.
