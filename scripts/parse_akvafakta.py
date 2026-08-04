#!/usr/bin/env python3
"""
Parse les rapports Akvafakta (hebdomadaires et mensuels) en JSON.

Usage :
    python3 scripts/parse_akvafakta.py

Lit tous les PDF de pdf/uke/ et pdf/mane/, met a jour data/data.json.
Les rapports deja presents dans le JSON ne sont pas reparsés : seuls les
nouveaux fichiers sont traités, donc relancer le script est peu couteux.

Prerequis : pdftotext (paquet poppler-utils sur Linux, poppler sur macOS).
"""
import re, subprocess, glob, json, io, os, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'data.json')

CLASSES = ['1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9+']
MONTHS = {'januar': 1, 'februar': 2, 'mars': 3, 'april': 4, 'mai': 5, 'juni': 6,
          'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
          'november': 11, 'desember': 12}


def pdftext(path, first=None, last=None):
    cmd = ['pdftotext', '-layout']
    if first: cmd += ['-f', str(first)]
    if last:  cmd += ['-l', str(last)]
    cmd += [path, '-']
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def num(s):
    """Convertit un nombre norvegien en float.
    Gere les espaces insecables ET l'apostrophe, qui apparait comme separateur
    dans certains rapports recents (ex. "9 600 000' kroner")."""
    s = s.replace('\u00a0', '').replace(' ', '').replace("'", '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------
#  HEBDOMADAIRE
# --------------------------------------------------------------------------
def parse_weekly(path):
    """
    Trois pieges de mise en page, tous rencontres sur 2018-2026 :
      1. Les pourcentages de calibre sont DECIMAUX avant 2023 (18,6 %) et
         ENTIERS ensuite (22 %). Le regex accepte les deux.
      2. Le tableau des prix a les memes en-tetes de colonnes que celui de la
         repartition, donc on cherche l'en-tete APRES le mot 'Fordeling'.
      3. La source change en semaine 18 de 2025 : NASDAQ puis Sitagri.
         Elle est enregistree dans le champ 'src' pour pouvoir recaler.
    """
    fname = os.path.basename(path)
    m = re.search(r'(\d{2})[-_](\d{2})\.pdf', fname)
    if not m:
        return None
    rec = {'file': fname,
           'report_year': 2000 + int(m.group(1)),
           'report_week': int(m.group(2))}
    txt = pdftext(path)
    lines = txt.split('\n')

    # --- repartition par classe de poids
    start = next((a for a, l in enumerate(lines) if 'Fordeling' in l), None)
    if start is not None:
        for a in range(start, min(start + 8, len(lines))):
            l = lines[a]
            if 'Uke' in l and '1-2 kg' in l and '8-9' in l:
                for l2 in lines[a + 1:a + 5]:
                    nums = [x.replace(',', '.') for x in
                            re.findall(r'(-?\d+(?:[,.]\d+)?)\s*%', l2)]
                    wk = re.match(r'\s*(\d+)\s', l2)
                    if len(nums) >= 9 and wk:
                        rec['dist_week'] = int(wk.group(1))
                        for c, v in zip(CLASSES, nums[:9]):
                            rec['sh_' + c] = float(v)
                        rec['sh_6plus'] = sum(float(v) for v in nums[5:9])
                        rec['sh_5plus'] = sum(float(v) for v in nums[4:9])
                        break
                break

    # --- prix par classe
    ps = txt.split('Prisutvikling')
    if len(ps) > 1:
        blk = ps[1].split('Endring sist uke')[0]
        cand = []
        for l in blk.split('\n'):
            v = re.findall(r'\d+,\d{2}', l)
            wk = re.match(r'\s*(\d+)\s', l)
            if len(v) >= 10 and wk:
                cand.append((int(wk.group(1)),
                             [float(x.replace(',', '.')) for x in v[:10]]))
        if cand:
            wk, v = cand[-1]          # derniere ligne = semaine la plus recente
            rec['price_week'] = wk
            for c, x in zip(CLASSES, v[:9]):
                rec['p_' + c] = x
            rec['p_avg'] = v[9]

    # --- source declaree (NASDAQ ou Sitagri)
    if 'Fordeling' in txt:
        ks = re.search(r'Kilde:\s*([^\n]{0,40})', txt.split('Fordeling')[1])
        rec['src'] = ks.group(1).strip() if ks else None

    return rec


# --------------------------------------------------------------------------
#  MENSUEL
# --------------------------------------------------------------------------
def parse_monthly(path):
    """
    Page de garde + table 7 (exports par pays).
    L'unite de la valeur d'export change trois fois entre 2019 et 2026 :
    on retient l'echelle qui place le prix implicite dans une fourchette
    plausible de 30 a 200 NOK/kg.
    """
    txt = pdftext(path)
    flat = re.sub(r'[ \t]+', ' ', txt)

    m = re.search(r'Endring fra\s*(\d{4})', flat)
    m2 = re.search(r'Status per utgangen av\s*\n\s*([A-Za-zæøåÆØÅ]+)', txt)
    if not m or not m2:
        return None
    mn = m2.group(1).strip().lower()
    if mn not in MONTHS:
        return None
    rec = {'file': os.path.basename(path),
           'year': int(m.group(1)) + 1,
           'month': MONTHS[mn]}

    li, oi = flat.find('Laks'), flat.find('rret', flat.find('Laks'))
    laks = flat[li:oi] if li >= 0 and oi > li else ''

    def grab(label, block):
        mm = re.search(label + r'\s+([\d \u00a0,.\']+)', block)
        return num(mm.group(1)) if mm else None

    rec['biomass_t'] = grab('Biomasse', laks)
    rec['export_t'] = grab('Eksportert kvantum', laks)
    rec['export_val'] = grab('Eksport verdi', laks)
    rec['smolt_mill'] = grab('Utsatt fisk', laks)
    rec['feed_t'] = grab(r'F.rforbruk', laks)
    mt = re.search(r'Temperatur\s+([\d,.]+)', flat)
    rec['temp'] = num(mt.group(1)) if mt else None

    rec['price_nok_kg'] = None
    if rec['export_val'] and rec['export_t']:
        # L'unite n'est pas indiquee de facon fiable : on retient l'echelle qui
        # place le prix implicite dans une fourchette plausible.
        for sc in (1e6, 1e3, 1):
            p = rec['export_val'] * sc / (rec['export_t'] * 1000)
            if 30 <= p <= 200:
                rec['price_nok_kg'] = round(p, 2)
                break

    # --- exports par pays (table 7)
    sec = txt.split('Eksport fordelt')
    if len(sec) > 1:
        blk = sec[1][:9000]
        for lbl, pat in [('kina', r'Kina og Hong Kong Totalt'), ('usa', r'\bUsa\b'),
                         ('eu', r'EU27 Totalt'), ('japan', r'Japan Totalt')]:
            for l in blk.split('\n'):
                mm = re.search(pat, l, re.I)
                if mm:
                    tail = re.sub(r'-?\s?\d+\s*%', '|', l[mm.end():])
                    v = [float(x.replace('\u00a0', '').replace(' ', ''))
                         for x in re.findall(r'\d[\d\u00a0 ]*\d|\d', tail)]
                    if len(v) >= 2 and v[0] > 100:
                        rec[lbl + '_q'], rec[lbl + '_v'] = v[0], v[1]
                        rec[lbl + '_p'] = round(v[1] / v[0], 2)
                    break
    return rec


# --------------------------------------------------------------------------
def main():
    if subprocess.run(['which', 'pdftotext'], capture_output=True).returncode:
        sys.exit("ERREUR : pdftotext introuvable.\n"
                 "  macOS  : brew install poppler\n"
                 "  Ubuntu : sudo apt install poppler-utils")

    data = json.load(io.open(DATA)) if os.path.exists(DATA) else {}
    for k in ('weekly', 'monthly_akvafakta', 'country'):
        data.setdefault(k, [])

    seen_w = {(r['report_year'], r['report_week']) for r in data['weekly']}
    seen_m = {(r['year'], r['month']) for r in data['monthly_akvafakta']}
    added_w = added_m = 0

    for f in sorted(glob.glob(os.path.join(ROOT, 'pdf', 'uke', '*.pdf'))):
        r = parse_weekly(f)
        if not r:
            print(f'  ignore (nom illisible) : {os.path.basename(f)}')
            continue
        key = (r['report_year'], r['report_week'])
        if key in seen_w:
            continue
        if 'sh_6plus' not in r and 'p_avg' not in r:
            print(f'  ATTENTION, rien extrait : {os.path.basename(f)}')
            continue
        data['weekly'].append(r); seen_w.add(key); added_w += 1

    for f in sorted(glob.glob(os.path.join(ROOT, 'pdf', 'mane', '*.pdf'))):
        r = parse_monthly(f)
        if not r:
            print(f'  ignore : {os.path.basename(f)}')
            continue
        key = (r['year'], r['month'])
        if key in seen_m:
            continue
        data['monthly_akvafakta'].append(r); seen_m.add(key); added_m += 1
        if any(k.endswith('_q') for k in r):
            data['country'] = [x for x in data['country']
                               if (x['year'], x['month']) != key]
            data['country'].append({k: v for k, v in r.items()
                                    if k in ('year', 'month') or '_' in k})

    data['weekly'].sort(key=lambda r: (r['report_year'], r['report_week']))
    data['monthly_akvafakta'].sort(key=lambda r: (r['year'], r['month']))
    data['country'].sort(key=lambda r: (r['year'], r['month']))
    data.setdefault('meta', {})
    data['meta'].update(generated=dt.date.today().isoformat(),
                        weeks=len(data['weekly']))

    io.open(DATA, 'w').write(json.dumps(data, separators=(',', ':')))
    print(f'\n{added_w} semaines et {added_m} mois ajoutes.')
    print(f'Total : {len(data["weekly"])} semaines, '
          f'{len(data["monthly_akvafakta"])} mois.')
    print(f'data.json : {os.path.getsize(DATA)/1e6:.1f} Mo')

    w = [r for r in data['weekly'] if 'sh_6plus' in r]
    if w:
        last = w[-1]
        print(f'\nDerniere semaine : {last["report_year"]} S{last.get("dist_week")}'
              f' — part 6+ {last["sh_6plus"]:.0f} %')


if __name__ == '__main__':
    main()
