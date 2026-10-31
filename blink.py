import os
import random
import tkinter as tk
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageTk

try: 
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ============== SETTINGS ==============
PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eye.jpg")
COLS     = 170        
CW, CH   = 6, 10        
FONT_PX  = 11
BG_MIX   = 0.55        
CH_BOOST = 1.30        
PUPIL_X  = 0.64         
PUPIL_Y  = 0.55         
VIGNETTE = 0.55         
IRIS_POP = 0.7          
BLINK_MS = 420
FRAME_MS = 30
CY_RATIO = 0.55        
# ======================================

CHARS = np.array(list(" .:-=+*#%@"))

# ---------- image -> ASCII couleur ----------
img = Image.open(PATH).convert("RGB")
w, h = img.size
rows = int(COLS * (h / w) * (CW / CH))
img = img.resize((COLS, rows), Image.LANCZOS)
img = ImageEnhance.Color(img).enhance(1.1)
img = ImageEnhance.Contrast(img).enhance(1.15)
img = ImageEnhance.Sharpness(img).enhance(1.6)

arr = np.asarray(img).astype(float)

# distance à la pupille (corrigée du ratio de l'image)
yy, xx = np.mgrid[0:rows, 0:COLS]
dx = (xx / COLS - PUPIL_X) * (w / h)
dy = (yy / rows - PUPIL_Y)
d = np.sqrt(dx ** 2 + dy ** 2)[..., None]

# 1) vignette : peau et bords plus sombres
vig = np.exp(-(d / 0.85) ** 2)
arr = arr * (1 - VIGNETTE + VIGNETTE * 1.25 * vig)

# 2) iris : plus saturé et plus lumineux
iris = np.exp(-(d / 0.17) ** 2)
lum = (arr @ np.array([0.299, 0.587, 0.114]))[..., None]
arr = lum + (arr - lum) * (1 + IRIS_POP * iris)
arr = arr * (1 + 0.35 * IRIS_POP * iris)
arr = np.clip(arr, 0, 255)

gray = arr @ np.array([0.299, 0.587, 0.114])
lo, hi = np.percentile(gray, 1), np.percentile(gray, 99)
g = np.clip((gray - lo) / (hi - lo), 0, 1)
idx = (g * (len(CHARS) - 1)).astype(int)

bg_small = np.clip(arr * BG_MIX, 0, 255).astype(np.uint8)
fg_small = np.clip(arr * CH_BOOST + 15, 0, 255).astype(np.uint8)

bg = np.repeat(np.repeat(bg_small, CH, axis=0), CW, axis=1)
ascii_img = Image.fromarray(bg)
draw = ImageDraw.Draw(ascii_img)

font = None
for name in ("consolab.ttf", "consola.ttf", "courbd.ttf", "cour.ttf"):
    try:
        font = ImageFont.truetype(name, FONT_PX)
        break
    except Exception:
        pass
if font is None:
    font = ImageFont.load_default()

for y in range(rows):
    for x in range(COLS):
        c = CHARS[idx[y, x]]
        if c != " ":
            draw.text((x * CW, y * CH), c, font=font,
                      fill=tuple(int(v) for v in fg_small[y, x]))

base = np.asarray(ascii_img)
H, W = base.shape[:2]

# ---------- paupières ----------
band = max(2, rows // 12)
SKIN_TOP = (bg_small[:band].reshape(-1, 3).mean(axis=0) * 0.9).astype(np.uint8)
SKIN_BOT = (bg_small[-band:].reshape(-1, 3).mean(axis=0) * 0.9).astype(np.uint8)
LASH = np.array([22, 10, 5], dtype=np.uint8)
LASH_PX = 4

ys = np.arange(H)[:, None]
u = np.linspace(-1, 1, W)
cy = H * CY_RATIO


def make_frame(openness):
    curve = 1.0 - 0.65 * (u ** 2) * (1.0 - openness)
    upper = cy - cy * openness * curve
    lower = cy + (H - cy) * openness * curve
    lower = np.maximum(lower, upper)

    out = base.copy()
    out[ys < upper] = SKIN_TOP
    out[ys > lower] = SKIN_BOT
    if openness < 0.9:
        out[(ys >= upper) & (ys < upper + LASH_PX)] = LASH
        out[(ys <= lower) & (ys > lower - LASH_PX)] = LASH
    return out


# ---------- fenêtre ----------
root = tk.Tk()
root.title("Hazel Eye")
root.configure(bg="black")
label = tk.Label(root, bg="black", bd=0)
label.pack()


def show(openness):
    photo = ImageTk.PhotoImage(Image.fromarray(make_frame(openness)))
    label.configure(image=photo)
    label.image = photo


show(1.0)

# ---------- animation ----------
blinking = False


def ease(t):
    return t * t * (3 - 2 * t)


def tick(now=0):
    global blinking
    if not blinking:
        return
    t = min(1.0, now / BLINK_MS)
    show(abs(1.0 - 2.0 * ease(t)))
    if t >= 1.0:
        blinking = False
        show(1.0)
        root.after(random.choice([200, random.randint(2200, 5500)]), start_blink)
        return
    root.after(FRAME_MS, tick, now + FRAME_MS)


def start_blink(event=None):
    global blinking
    if not blinking:
        blinking = True
        tick(0)


root.bind("<space>", start_blink)
root.after(1500, start_blink)
root.mainloop()