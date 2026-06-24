"""
Actualizar JS de datos del dashboard hasta Jun 23, 2026.
Fuentes: blip_whatsapp_logs + voximplant_whatsapp_logs (DB)
         + Active Campaign retargeting (preservado del template_data existente)
"""
import json
from collections import defaultdict

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun"]
YM_TO_KEY = {"2026-01": "ene", "2026-02": "feb", "2026-03": "mar",
             "2026-04": "abr", "2026-05": "may", "2026-06": "jun"}
MONTH_IDX = {"ene": 3, "feb": 4, "mar": 5, "abr": 6, "may": 7, "jun": 8}

# ============================================================
# Load DB extracts
# ============================================================
print("Loading DB extracts...")
with open("_blip_extract.json") as f:
    blip_tpl = json.load(f)  # [template_name, ym, count]
with open("_vox_extract.json") as f:
    vox_tpl = json.load(f)
with open("_blip_phone_month.json") as f:
    blip_phone = json.load(f)  # [phone, ym, count]
with open("_vox_phone_month.json") as f:
    vox_phone = json.load(f)
with open("_blip_tpl_phone_month.json") as f:
    blip_tpl_phone = json.load(f)  # [template, phone, ym, count]
with open("_vox_tpl_phone_month.json") as f:
    vox_tpl_phone = json.load(f)

# ============================================================
# Load existing template_data to preserve categories + AC data
# ============================================================
print("Loading existing template_data.js...")
with open("template_data.js", "r", encoding="utf-8") as f:
    raw = f.read()
old_data = json.loads(raw[len("const templateData = "):].rstrip().rstrip(";"))

# Build lookup: (provider, template_name) -> {category, meta_category}
old_lookup = {}
for row in old_data:
    old_lookup[(row[0], row[1])] = {
        "category": row[2],
        "meta": row[10]
    }

# ============================================================
# 1. BUILD template_data.js
# ============================================================
print("\n=== Rebuilding template_data.js ===")

# Aggregate DB data by template
db_templates = defaultdict(lambda: defaultdict(int))
for name, ym, cnt in blip_tpl:
    mk = YM_TO_KEY.get(ym)
    if mk:
        db_templates[("blip", name)][mk] += cnt

for name, ym, cnt in vox_tpl:
    mk = YM_TO_KEY.get(ym)
    if mk:
        db_templates[("voximplant", name)][mk] += cnt

# Build new template_data
new_data = []
seen = set()  # track (provider, name) pairs

# First: DB templates
for (prov, name), months in db_templates.items():
    info = old_lookup.get((prov, name), {})
    cat = info.get("category", "sin_clasificar")
    meta = info.get("meta", "MARKETING")

    row = [prov, name, cat,
           months.get("ene", 0), months.get("feb", 0), months.get("mar", 0),
           months.get("abr", 0), months.get("may", 0), months.get("jun", 0),
           0, meta]
    row[9] = sum(row[3:9])
    if row[9] > 0:
        new_data.append(row)
        seen.add((prov, name))

# Second: non-DB templates from existing data (Botmaker, AC retargeting, etc.)
ac_preserved = 0
for row in old_data:
    key = (row[0], row[1])
    if key not in seen:
        new_data.append(row)
        seen.add(key)
        ac_preserved += 1

# Sort by total descending
new_data.sort(key=lambda x: -x[9])

print(f"  DB templates: {len(db_templates)}")
print(f"  AC/preserved templates: {ac_preserved}")
print(f"  Total templates: {len(new_data)}")

# Verify totals by month
for m in MONTHS:
    idx = MONTH_IDX[m]
    total = sum(row[idx] for row in new_data)
    print(f"  {m}: {total:,}")

with open("template_data.js", "w", encoding="utf-8") as f:
    f.write("const templateData = " + json.dumps(new_data, ensure_ascii=False) + ";")
print("  Written template_data.js")

# ============================================================
# 2. BUILD template_totals.js
# ============================================================
print("\n=== Rebuilding template_totals.js ===")

totals = {}
for m in MONTHS:
    idx = MONTH_IDX[m]
    by_area = defaultdict(int)
    by_meta = defaultdict(int)
    grand = 0
    for row in new_data:
        v = row[idx]
        if v > 0:
            by_area[row[2]] += v
            by_meta[row[10]] += v
            grand += v
    totals[m] = {
        "grand": grand,
        "byArea": dict(by_area),
        "byMeta": dict(by_meta)
    }
    print(f"  {m}: grand={grand:,}")

with open("template_totals.js", "w", encoding="utf-8") as f:
    f.write("const templateTotals = " + json.dumps(totals, ensure_ascii=False) + ";")
print("  Written template_totals.js")

# ============================================================
# 3. BUILD phone_inline.js
# ============================================================
print("\n=== Rebuilding phone_inline.js ===")

# Aggregate phone data from DB
phone_data = defaultdict(lambda: defaultdict(int))
for ph, ym, cnt in blip_phone:
    mk = YM_TO_KEY.get(ym)
    if mk:
        phone_data[mk][ph] += cnt

for ph, ym, cnt in vox_phone:
    mk = YM_TO_KEY.get(ym)
    if mk:
        phone_data[mk][ph] += cnt

# Load existing phone_inline to merge AC data
with open("phone_inline.js", "r", encoding="utf-8") as f:
    raw = f.read()
old_phone_data = json.loads(raw[len("const allPhoneData = "):].rstrip().rstrip(";"))

# For each month, merge: DB data + any AC phones not in DB
# AC phones were added by incorporate_ac.py, which added phone counts
# We can identify AC-only phones as those in old data but not in DB for that month
# However, since we can't reliably separate AC from DB in old data,
# and AC templates are primarily retargeting that might also be in DB,
# let's use DB as the primary source and only add AC delta for ene-may
# For simplicity, use DB data as-is (it's the source of truth for DB templates)

result_phone = {}
for m in MONTHS:
    db_phones = phone_data[m]
    # Also check old data for AC-only phones
    old_month = {row[0]: row[1] for row in old_phone_data.get(m, [])}

    # Start with DB phones
    merged = dict(db_phones)

    # For phones in old data but NOT in DB, they might be AC-only
    # Check if the count difference suggests AC additions
    # Actually, old data = DB + AC merged. DB data alone might be less.
    # For months ene-may (complete in DB), the difference is AC.
    # For jun, we have DB through Jun 23 which should be > old Jun 12.
    # Let's compute the AC delta
    if m != "jun":
        for ph, old_cnt in old_month.items():
            if ph not in merged:
                # Phone only in old data = AC-only phone
                merged[ph] = old_cnt
            else:
                # Phone in both: if old > DB, the diff is AC
                if old_cnt > merged[ph]:
                    merged[ph] = old_cnt

    # Convert to sorted list [phone, msgs, cost]
    # Cost = 0 placeholder (calculated in HTML based on blended rate)
    phone_list = sorted([[ph, cnt, 0] for ph, cnt in merged.items()],
                        key=lambda x: -x[1])
    result_phone[m] = phone_list
    print(f"  {m}: {len(phone_list):,} phones, {sum(cnt for _, cnt, _ in phone_list):,} msgs")

with open("phone_inline.js", "w", encoding="utf-8") as f:
    f.write("const allPhoneData = " + json.dumps(result_phone, ensure_ascii=False) + ";")
print("  Written phone_inline.js")

# ============================================================
# 4. BUILD template_phones.js
# ============================================================
print("\n=== Rebuilding template_phones.js ===")

# Aggregate template × phone × month from DB
tpl_phone_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
for tpl, ph, ym, cnt in blip_tpl_phone:
    mk = YM_TO_KEY.get(ym)
    if mk:
        tpl_phone_data[mk][tpl][ph] += cnt

for tpl, ph, ym, cnt in vox_tpl_phone:
    mk = YM_TO_KEY.get(ym)
    if mk:
        tpl_phone_data[mk][tpl][ph] += cnt

# Load existing for AC merge
with open("template_phones.js", "r", encoding="utf-8") as f:
    raw = f.read()
old_tpl_phones = json.loads(raw[len("const templatePhones = "):].rstrip().rstrip(";"))

result_tpl_phones = {}
for m in MONTHS:
    db_month = tpl_phone_data[m]
    old_month = old_tpl_phones.get(m, {})

    merged = {}
    # DB templates
    for tpl, phones in db_month.items():
        phone_list = sorted([[ph, cnt] for ph, cnt in phones.items()],
                            key=lambda x: -x[1])
        merged[tpl] = phone_list

    # AC-only templates (in old but not in DB)
    if m != "jun":
        for tpl, phone_list in old_month.items():
            if tpl not in merged:
                merged[tpl] = phone_list

    result_tpl_phones[m] = merged
    print(f"  {m}: {len(merged)} templates")

with open("template_phones.js", "w", encoding="utf-8") as f:
    f.write("const templatePhones = " + json.dumps(result_tpl_phones, ensure_ascii=False) + ";")
print("  Written template_phones.js")

# ============================================================
# 5. BUILD dias_atraso_data.js
# ============================================================
print("\n=== Rebuilding dias_atraso_data.js ===")

# Map template names to dias_atraso buckets
def classify_dias_atraso(tpl_name, provider):
    n = tpl_name.lower()
    if provider == "voximplant" and "moderada" in n:
        return "moderada"
    if provider == "botmaker":
        if "preventivo" in n:
            return "gestor_prev"
        return "gestor"
    # Blip cobranza templates
    if "autoreprogramacion" in n:
        return "autoreprog"
    if "preventivo1" in n or "preventivo_video_1" in n:
        return "-1"
    if "preventivo2" in n or "preventivo_video_2" in n:
        return "-2"
    if "preventivo3" in n:
        return "-3"
    if "preventivo4" in n:
        return "-4"
    if "recordatorio_grupo" in n or "blip_recordatorio" in n:
        return "-1"
    if n == "preventivo" or "preventivo" in n:
        return "preventivo"
    if "dia_0" in n or n.endswith("_dia_0"):
        return "0"
    if "dia_3" in n and "dia_3_" not in n:
        return "3"
    if "dia_10" in n and "dia_10_" not in n:
        return "10"
    if "dia_1_a_3" in n or "de_1_a_3" in n:
        return "1-3"
    if "dia_4_a_5" in n or "de_4_a_5" in n:
        return "4-5"
    if "dia_6_a_10" in n or "de_6_a_10" in n:
        return "6-10"
    if "dia_11_a_15" in n or "de_11_a_15" in n:
        return "11-15"
    if "dia_16_a_30" in n or "de_16_a_30" in n or "dia_16_a_20" in n or "de_16_a_20" in n:
        return "16-30"
    # New naming convention in May/Jun
    if "_dia_" in n:
        # Try to extract day number
        import re
        m_day = re.search(r'dia_(\d+)', n)
        if m_day:
            day = int(m_day.group(1))
            if day == 0: return "0"
            if day <= 3: return str(day)
            if day <= 5: return "4"
            if day <= 10: return "6"
            if day <= 15: return "11"
            return "16"
    # Moroso templates with risk levels (new naming)
    if "moroso_de_" in n:
        import re
        m2 = re.search(r'moroso_de_(\d+)(?:_a_(\d+))?', n)
        if m2:
            start = int(m2.group(1))
            if start == 0: return "0"
            if start <= 3: return "1-3"
            if start <= 5: return "4-5"
            if start <= 10: return "6-10"
            if start <= 15: return "11-15"
            if start <= 20: return "16-20"
            return "16-30"
    if "moroso_otros" in n or "mora_otro" in n:
        return "moroso_otros"
    return None

# Build dias_atraso_data from template × phone data
dias_data = {}
for m in MONTHS:
    ym = f"2026-{MONTHS.index(m)+1:02d}"
    buckets = defaultdict(lambda: {"msgs": 0, "phones": set()})

    # Get cobranza templates for this month
    month_tpl_phones = tpl_phone_data.get(m, {})

    for row in new_data:
        tpl_name = row[1]
        provider = row[0]
        cat = row[2]
        idx = MONTH_IDX[m]
        vol = row[idx]
        if vol == 0:
            continue
        if cat not in ("cobranza_mora", "cobranza_preventiva"):
            continue

        bucket = classify_dias_atraso(tpl_name, provider)
        if bucket is None:
            continue

        buckets[bucket]["msgs"] += vol

        # Count unique phones from template_phones data
        if tpl_name in month_tpl_phones:
            for ph, cnt in month_tpl_phones[tpl_name].items():
                buckets[bucket]["phones"].add(ph)
        elif m != "jun":
            # Check old tpl_phones for AC templates
            old_m = old_tpl_phones.get(m, {})
            if tpl_name in old_m:
                for entry in old_m[tpl_name]:
                    buckets[bucket]["phones"].add(entry[0])

    dias_data[ym] = {k: {"msgs": v["msgs"], "phones": len(v["phones"])}
                     for k, v in buckets.items() if v["msgs"] > 0}

    total_msgs = sum(v["msgs"] for v in dias_data[ym].values())
    print(f"  {ym}: {len(dias_data[ym])} buckets, {total_msgs:,} msgs")

with open("dias_atraso_data.js", "w", encoding="utf-8") as f:
    f.write("const diasAtrasoData = " + json.dumps(dias_data, ensure_ascii=False) + ";")
print("  Written dias_atraso_data.js")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("RESUMEN DE ACTUALIZACION")
print("=" * 60)
print(f"Periodo: Enero - Junio 23, 2026")
print(f"Templates totales: {len(new_data)}")
for m in MONTHS:
    idx = MONTH_IDX[m]
    total = sum(row[idx] for row in new_data)
    print(f"  {m}: {total:,} msgs")
print(f"\nArchivos actualizados:")
print(f"  - template_data.js")
print(f"  - template_totals.js")
print(f"  - phone_inline.js")
print(f"  - template_phones.js")
print(f"  - dias_atraso_data.js")
