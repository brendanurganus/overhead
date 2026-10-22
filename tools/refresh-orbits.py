"""OverHead orbit refresh.

Updates the orbital elements in OverHead's data/sats.json from public mirrors of
CelesTrak / Space-Track data, adds newly launched satellites, and drops satellites
whose public orbit data has gone stale. Owner, launch and mission details for
existing satellites are kept as they are.

Usage: python3 refresh-orbits.py CURRENT_SATS_JSON OUTPUT_DIR [--force]
  Writes OUTPUT_DIR/data/sats.json.
  Exit 0: refreshed.  Exit 3: not due yet (refreshed under 20 hours ago; use --force).
  Any other nonzero exit: failed, nothing written.
Needs: Python 3 standard library only; network access to raw.githubusercontent.com and db.satnogs.org.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

MIRROR = 'https://raw.githubusercontent.com/satvisorcom/satvisor-data/master'
STARLINK_TLE = ['https://raw.githubusercontent.com/dylanfain/LEOrbit/main/public/data/starlink.tle',
                'https://raw.githubusercontent.com/dylanfain/LEOrbit/master/public/data/starlink.tle']
SATNOGS = 'https://db.satnogs.org/api/tle/?format=json'
GROUP_CAT = {
    'stations': 'stations', 'starlink': 'starlink',
    'oneweb': 'broadband', 'kuiper': 'broadband', 'qianfan': 'broadband', 'hulianwang': 'broadband',
    'gnss': 'nav', 'gps-ops': 'nav', 'glo-ops': 'nav', 'galileo': 'nav', 'beidou': 'nav', 'sbas': 'nav',
    'weather': 'weather', 'noaa': 'weather', 'goes': 'weather', 'military': 'military',
    'resource': 'imaging', 'planet': 'imaging', 'spire': 'imaging', 'dmc': 'imaging',
    'science': 'science', 'geodetic': 'science', 'education': 'science', 'engineering': 'science', 'radar': 'science',
    'iridium-NEXT': 'comms', 'globalstar': 'comms', 'orbcomm': 'comms', 'intelsat': 'comms', 'ses': 'comms',
    'eutelsat': 'comms', 'telesat': 'comms', 'tdrss': 'comms', 'amateur': 'comms', 'x-comm': 'comms',
    'other-comm': 'comms', 'geo': 'comms', 'cubesat': 'science', 'satnogs': 'other', 'last-30-days': 'other', 'active': 'other',
}
# category hints for newly launched satellites, checked in order
NAME_CAT = [
    (r'^STARLINK', 'starlink'), (r'^(ONEWEB|KUIPER|QIANFAN|HULIANWANG|GUOWANG)', 'broadband'),
    (r'^(YAOGAN|USA |NROL|COSMOS|KOSMOS|SHIYAN|TJS|OFEQ)', 'military'),
    (r'^(ICEYE|STRIX|CAPELLA|UMBRA|SKYSAT|FLOCK|DOVE|PELICAN|NEONSAT|WORLDVIEW|LEGION|JILIN|SUPERVIEW|GAOFEN|SENTINEL|LANDSAT|CBERS|KOMPSAT|SAR)', 'imaging'),
    (r'^(TOMORROW|FENGYUN|NOAA|GOES|METOP|METEOSAT|HIMAWARI|METEOR|JPSS)', 'weather'),
    (r'^(GPS|NAVSTAR|BEIDOU|GALILEO|GLONASS|QZS|IRNSS|NVS)', 'nav'),
    (r'^(SATELIOT|IRIDIUM|GLOBALSTAR|ORBCOMM|SWARM|LYNK|BLUEBIRD|SPACEMOBILE|AST |ECHOSTAR|INTELSAT|SES|EUTELSAT|VIASAT|INMARSAT|ZHONGXING|CHINASAT|APSTAR)', 'comms'),
]
A5 = 'ABCDEFGHJKLMNPQRSTUVWXYZ'


def fetch(url, tries=3, timeout=180):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'OverHead-refresh/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print(f'  {url}: attempt {k + 1} failed: {e}', file=sys.stderr)
            time.sleep(4 * (k + 1))
    return None


def a5(s):
    s = s.strip()
    return (A5.index(s[0].upper()) + 10) * 10000 + int(s[1:]) if s and s[0].isalpha() else int(s)


def expo(s):
    s = s.strip()
    if not s or s in ('00000-0', '00000+0'):
        return 0.0
    sign = -1 if s[0] == '-' else 1
    s = s.lstrip('+-')
    return sign * float('0.' + s[:-2]) * 10 ** int(s[-2:])


def intl_from_tle(s):
    s = s.strip()
    if len(s) < 5:
        return ''
    yy = int(s[:2])
    return f"{2000 + yy if yy < 57 else 1900 + yy}-{s[2:5]}{s[5:]}"


def tle_to_omm(name, l1, l2):
    yy, doy = int(l1[18:20]), float(l1[20:32])
    ep = dt.datetime(2000 + yy if yy < 57 else 1900 + yy, 1, 1) + dt.timedelta(days=doy - 1)
    return {
        'OBJECT_NAME': name.strip(), 'OBJECT_ID': intl_from_tle(l1[9:17]), 'NORAD_CAT_ID': a5(l1[2:7]),
        'EPOCH': ep.strftime('%Y-%m-%dT%H:%M:%S.%f'), 'MEAN_MOTION_DOT': float(l1[33:43]),
        'MEAN_MOTION_DDOT': expo(l1[44:52]), 'BSTAR': expo(l1[53:61]), 'INCLINATION': float(l2[8:16]),
        'RA_OF_ASC_NODE': float(l2[17:25]), 'ECCENTRICITY': float('0.' + l2[26:33].strip()),
        'ARG_OF_PERICENTER': float(l2[34:42]), 'MEAN_ANOMALY': float(l2[43:51]), 'MEAN_MOTION': float(l2[52:63]),
    }


def g(v, n):
    return 0 if v == 0 else float(f'{v:.{n}g}')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force = '--force' in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    cur_path, out_dir = args
    d = json.load(open(cur_path, encoding='utf-8'))
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    last = d.get('orbitRefreshed')
    if last and not force:
        age_h = (now - dt.datetime.fromisoformat(last.rstrip('Z'))).total_seconds() / 3600
        if age_h < 20:
            print(f'not due: orbits refreshed {age_h:.1f} hours ago')
            sys.exit(3)

    F = {f: i for i, f in enumerate(d['fields'])}
    cat_index = {c['id']: k for k, c in enumerate(d['cats'])}
    pool, group_of, sources = {}, {}, []

    # SatNOGS also tracks long-dead satellites, and the 'active' list is months old,
    # so neither may add new satellites; they only refresh ones already listed
    no_add = {'satnogs', 'active'}

    def offer(x, grp=None):
        n = x['NORAD_CAT_ID']
        if grp and grp not in no_add and n not in group_of:
            group_of[n] = grp
        cur = pool.get(n)
        if cur is None or x['EPOCH'] > cur['EPOCH']:
            if cur is not None and not x.get('OBJECT_ID'):
                x['OBJECT_ID'] = cur.get('OBJECT_ID', '')
            pool[n] = x

    # 1) CelesTrak groups via the satvisor-data mirror (refreshed every 2 to 12 hours)
    for grp in GROUP_CAT:
        raw = fetch(f'{MIRROR}/celestrak/json/{grp}.json')
        if not raw:
            continue
        try:
            arr = json.loads(raw)
        except ValueError:
            continue
        for x in arr:
            offer(dict(x), grp)
        sources.append(f'{grp}:{len(arr)}')
    # 2) fresher Starlink elements (LEOrbit daily mirror)
    for url in STARLINK_TLE:
        raw = fetch(url)
        if not raw:
            continue
        lines = [l.rstrip() for l in raw.decode('latin-1').splitlines() if l.strip()]
        n = 0
        for i in range(len(lines) - 2):
            if lines[i + 1].startswith('1 ') and lines[i + 2].startswith('2 ') and not lines[i].startswith(('1 ', '2 ')):
                try:
                    offer(tle_to_omm(lines[i], lines[i + 1], lines[i + 2]), 'starlink'); n += 1
                except (ValueError, IndexError):
                    pass
        sources.append(f'leorbit-starlink:{n}')
        break
    # 3) SatNOGS, only to refresh satellites already known
    raw = fetch(SATNOGS)
    if raw:
        n = 0
        for e in json.loads(raw):
            k = e.get('norad_cat_id')
            if k in pool:
                try:
                    o = tle_to_omm(pool[k]['OBJECT_NAME'], e['tle1'], e['tle2']); offer(o); n += 1
                except (ValueError, KeyError, IndexError):
                    pass
        sources.append(f'satnogs:{n}')
    if len(pool) < 5000:
        sys.exit(f'too little orbit data arrived ({len(pool)} satellites); keeping the previous orbits')
    stdmag = {}
    raw = fetch(f'{MIRROR}/catalog/stdmag.json')
    if raw:
        try:
            stdmag = json.loads(raw)
        except ValueError:
            pass

    def age_days(epoch):
        return (now - dt.datetime.fromisoformat(epoch[:19])).total_seconds() / 86400

    def keep(epoch, mm):
        a = age_days(epoch)
        return a <= 21 or (mm < 6 and a < 120)

    def put(row, x):
        row[F['epoch']] = x['EPOCH']
        row[F['mm']] = g(float(x['MEAN_MOTION']), 11); row[F['ecc']] = g(float(x['ECCENTRICITY']), 7)
        row[F['inc']] = g(float(x['INCLINATION']), 7); row[F['raan']] = g(float(x['RA_OF_ASC_NODE']), 7)
        row[F['argp']] = g(float(x['ARG_OF_PERICENTER']), 7); row[F['ma']] = g(float(x['MEAN_ANOMALY']), 7)
        row[F['bstar']] = g(float(x['BSTAR']), 6); row[F['ndot']] = g(float(x['MEAN_MOTION_DOT']), 6)
        row[F['nddot']] = g(float(x['MEAN_MOTION_DDOT']), 6)

    rows, known = [], set()
    updated = dropped = 0
    for row in d['rows']:
        n = row[F['norad']]
        known.add(n)
        x = pool.get(n)
        if x and x['EPOCH'] > row[F['epoch']]:
            put(row, x); updated += 1
        if keep(row[F['epoch']], row[F['mm']]):
            rows.append(row)
        else:
            dropped += 1
    # module duplicates that sit on top of the main station entries
    hide = {25575, 26400, 26700, 49044, 36086, 53239, 54216}
    added = 0
    for n, x in pool.items():
        if n in known or n in hide or n not in group_of or not keep(x['EPOCH'], float(x['MEAN_MOTION'])):
            continue
        name = x.get('OBJECT_NAME', str(n)).strip()
        if re.search(r'\b(DEB|R/B|AKM|PKM|OBJECT [A-Z]+)\b', name):
            continue
        cat = GROUP_CAT.get(group_of[n], 'other')
        for pat, c in NAME_CAT:
            if re.match(pat, name):
                cat = c
                break
        intl = x.get('OBJECT_ID', '') or ''
        m = re.match(r'(\d{4})-', intl)
        row = [None] * len(d['fields'])
        row[F['norad']] = n; row[F['name']] = name; row[F['display']] = 0; row[F['intl']] = intl
        put(row, x)
        row[F['cat']] = cat_index.get(cat, cat_index.get('other', 0))
        for f in ('owner', 'state', 'site', 'vehicle', 'maker', 'program', 'desc'):
            row[F[f]] = ''
        row[F['launch']] = m.group(1) if m else ''
        mag = stdmag.get(str(n))
        row[F['stdmag']] = mag if mag is not None else ''
        row[F['mass']] = ''
        rows.append(row); added += 1
    if len(rows) < 0.7 * len(d['rows']):
        sys.exit(f'refresh would shrink the catalog from {len(d["rows"])} to {len(rows)}; keeping the previous orbits')
    epochs = sorted(r[F['epoch']] for r in rows)
    d['rows'] = rows
    d['orbitUpdated'] = epochs[len(epochs) // 2][:19] + 'Z'
    d['orbitNewest'] = epochs[-1][:19] + 'Z'
    d['orbitRefreshed'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    os.makedirs(os.path.join(out_dir, 'data'), exist_ok=True)
    with open(os.path.join(out_dir, 'data', 'sats.json'), 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
    ages = sorted(age_days(e) for e in epochs)
    print(json.dumps({'satellites': len(rows), 'updated': updated, 'added': added, 'dropped': dropped,
                      'median_age_days': round(ages[len(ages) // 2], 2), 'orbitUpdated': d['orbitUpdated'],
                      'sources': sources}))


if __name__ == '__main__':
    main()
