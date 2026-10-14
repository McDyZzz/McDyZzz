"""Build index.html: the profile README as GitHub renders it, in four frames.

Run: python3 build_preview.py   (needs the gh CLI, signed in; writes index.html next to this file)
Input: ../README.md and the images in ../assets/.

Frames: desktop light, desktop dark (browser window 1280 px, README width 846 px) and
phone light, phone dark (window 375 px, README width 293 px).
The page is static HTML with no scripts. A <base href="../"> points at the repo root, so the
README's relative image paths (assets/...) load from ../assets/.
Each frame resolves every <picture> the way the browser would for that window width and theme:
the first <source> whose media query matches wins, else the <img> src. The <img> keeps its own
attributes (width, alt), so sizing and wrapping match GitHub. The viewer's own screen size and OS
theme have no effect.
"""
import html
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
D = pathlib.Path(__file__).resolve().parent
ROOT = D.parent

# name, label, window width, README width, theme
FRAMES = [
    ('desktop-light', 'Desktop · light · window 1280 px · README 846 px', 1280, 846, 'light'),
    ('desktop-dark', 'Desktop · dark · window 1280 px · README 846 px', 1280, 846, 'dark'),
    ('phone-light', 'Phone · light · window 375 px · README 293 px', 375, 293, 'light'),
    ('phone-dark', 'Phone · dark · window 375 px · README 293 px', 375, 293, 'dark'),
]


def render(md_path):
    """GitHub's own GFM renderer (gh api markdown), in the profile repo's context."""
    return subprocess.run(
        ["gh", "api", "markdown", "-f", "text=" + md_path.read_text(encoding="utf-8"),
         "-f", "mode=gfm", "-f", "context=McDyZzz/McDyZzz"],
        check=True, capture_output=True, text=True).stdout


FEATURE = re.compile(r'\(\s*(min-width|max-width|prefers-color-scheme)\s*:\s*([^)]+?)\s*\)')


def matches(media, window, theme):
    """Evaluates a media query made of (min-width), (max-width) and (prefers-color-scheme) joined by 'and'."""
    rest = FEATURE.sub('', media).replace('and', '').strip()
    assert not rest, 'unsupported media query: ' + media
    for name, value in FEATURE.findall(media):
        if name == 'min-width' and not window >= float(value.rstrip('px')):
            return False
        if name == 'max-width' and not window <= float(value.rstrip('px')):
            return False
        if name == 'prefers-color-scheme' and value != theme:
            return False
    return True


PICTURE = re.compile(r'<picture>(.*?)</picture>', re.S)
SOURCE = re.compile(r'<source media="([^"]+)" srcset="([^"]+)">')


def resolve(body, window, theme):
    """Replaces each <picture> with a <picture> holding only its <img>, src set to the file the browser picks."""
    def one(m):
        inner = m.group(1)
        img = re.search(r'<img[^>]*>', inner).group(0)
        pick = re.search(r' src="([^"]+)"', img).group(1)
        for media, srcset in SOURCE.findall(inner):
            if matches(html.unescape(media), window, theme):
                pick = srcset
                break
        return '<picture>%s</picture>' % re.sub(r' src="[^"]+"', ' src="%s"' % pick, img, count=1)
    out = PICTURE.sub(one, body)
    assert '<source' not in out
    return out


body = render(ROOT / "README.md")
assert body.count("<picture>") == 8, "expected 8 pictures"

frames = []
for name, label, window, width, theme in FRAMES:
    frames.append(
        '<section class="col %s" id="%s"><div class="label">%s</div>'
        '<div class="frame" style="--w:%dpx"><div class="bar">McDyZzz / README.md</div>'
        '<article class="markdown-body">%s</article></div></section>'
        % (theme, name, label, width, resolve(body, window, theme)))

page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<base href="../">
<title>Profile Preview</title>
<style>
/* Each frame carries its own GitHub palette. Values follow GitHub's light and dark themes. */
.light{color-scheme:light;--bg:#ffffff;--fg:#1f2328;--muted:#59636e;--border:#d1d9e0;--accent:#0969da}
.dark{color-scheme:dark;--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--border:#30363d;--accent:#4493f8}
*{box-sizing:border-box}
html,body{margin:0}
body{background:#0d1117;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}
.grid{display:flex;flex-wrap:wrap;align-items:flex-start}
.col{background:var(--bg);color:var(--fg);padding:24px 24px 48px}
.label{margin:0 0 12px;font-size:12px;color:var(--muted)}
/* The frame is GitHub's README box: 1 px border, 24 px padding, so the content box is exactly --w wide. */
.frame{width:calc(var(--w) + 50px);border:1px solid var(--border);border-radius:6px;overflow:hidden}
.bar{padding:8px 16px;border-bottom:1px solid var(--border);font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
/* GitHub markdown-body subset */
.markdown-body{width:calc(var(--w) + 48px);padding:24px;font-size:16px;line-height:1.5;overflow-wrap:break-word;color:var(--fg)}
.markdown-body>*:first-child{margin-top:0!important}
.markdown-body>*:last-child{margin-bottom:0!important}
.markdown-body p,.markdown-body details{margin-top:0;margin-bottom:16px}
.markdown-body a{color:var(--accent);text-decoration:none}
.markdown-body img{border-style:none;max-width:100%;box-sizing:content-box;background-color:var(--bg)}
.markdown-body summary{cursor:pointer}
</style></head>
<body><div class="grid">
__FRAMES__
</div></body></html>
""".replace("__FRAMES__", "\n".join(frames))
(D / "index.html").write_text(page, encoding="utf-8")
print(len(page))
