"""OverHead cloud refresh.

Downloads NASA GIBS imagery and rebuilds the page's cloud textures:
  tex/day_today.jpg   true-color Earth with the latest clouds (8192 x 4096)
  tex/clouds_daily.jpg  cloud mask used to dim ocean glint and city lights (4096 x 2048)
  data/clouds.json    when the imagery was fetched and which dates it covers

Usage: python3 refresh-clouds.py OUTPUT_DIR
Needs: Python 3 with numpy and Pillow, network access to gibs.earthdata.nasa.gov.
Exit code 0 on success; nonzero (with a message) if too little imagery arrived.
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
W, H = 8192, 4096
WMS = ('https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0'
       '&CRS=EPSG:4326&BBOX=-90,-180,90,180&STYLES=&WIDTH={w}&HEIGHT={h}&FORMAT=image/jpeg&LAYERS={layer}{time}')


def get(layer, date=None, tries=3):
    url = WMS.format(w=W, h=H, layer=layer, time=f'&TIME={date}' if date else '')
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=240) as r:
                data = r.read()
            if data[:2] != b'\xff\xd8':
                raise ValueError('not a JPEG: ' + data[:200].decode('latin-1'))
            return np.asarray(Image.open(io.BytesIO(data)).convert('RGB')).astype(np.float32)
        except Exception as e:  # network hiccups: retry, then give up on this layer
            print(f'  {layer} {date}: attempt {k + 1} failed: {e}', file=sys.stderr)
            time.sleep(5 * (k + 1))
    return None


def lum(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


def main():
    now = dt.datetime.now(dt.timezone.utc)
    dates = [(now - dt.timedelta(days=d)).strftime('%Y-%m-%d') for d in (0, 1, 2)]
    print('fetching cloud-free base')
    base = get('BlueMarble_NextGeneration')
    if base is None:
        sys.exit('could not download the Blue Marble base image')
    comp = np.zeros_like(base)
    filled = np.zeros(base.shape[:2], bool)
    used = []
    for date in dates:
        for sat in ('NOAA20', 'NOAA21', 'SNPP'):
            a = get(f'VIIRS_{sat}_CorrectedReflectance_TrueColor', date)
            if a is None:
                continue
            valid = a.sum(-1) > 18
            valid = np.asarray(Image.fromarray((valid * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 128
            take = valid & ~filled
            if take.mean() > 0.001:
                comp[take] = a[take]
                filled |= take
                used.append(f'{sat} {date}')
            print(f'  {sat} {date}: +{take.mean():.3f} -> {filled.mean():.3f}')
        if filled.mean() > 0.9:
            break
    if filled.mean() < 0.5:
        sys.exit(f'only {filled.mean():.0%} of the globe had imagery; keeping the previous clouds')
    m = Image.fromarray((filled * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    w = (np.asarray(m).astype(np.float32) / 255.0)[..., None]
    comp = comp * w + base * (1 - w)
    os.makedirs(os.path.join(OUT, 'tex'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
    Image.fromarray(comp.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, 'tex', 'day_today.jpg'), quality=84, optimize=True, progressive=True)
    # cloud estimate: brighter and greyer than the cloud-free base
    lt, lb = lum(comp) / 255.0, lum(base) / 255.0
    sat_ = (comp.max(-1) - comp.min(-1)) / (comp.max(-1) + 1)
    cloud = np.clip((lt - lb - 0.04) / np.maximum(0.12, 0.85 - lb), 0, 1) * np.clip(1.4 - sat_ * 2.2, 0, 1) * w[..., 0]
    Image.fromarray((cloud * 255).astype(np.uint8)).resize((4096, 2048), Image.LANCZOS).save(os.path.join(OUT, 'tex', 'clouds_daily.jpg'), quality=86, optimize=True)
    info = {'updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'dates': sorted({u.split()[1] for u in used}, reverse=True), 'passes': used, 'coverage': round(float(filled.mean()), 3)}
    with open(os.path.join(OUT, 'data', 'clouds.json'), 'w') as f:
        json.dump(info, f)
    print(json.dumps(info))


if __name__ == '__main__':
    main()
