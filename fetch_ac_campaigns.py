"""
Fetch Active Campaign data from Blip API and update JS files.
Replicates the Power Query in Blip_campañas.txt
"""
import json, urllib.request, time
from collections import defaultdict
from datetime import datetime

API_URL = "https://baldecash.http.msging.net/commands"
AUTH_KEY = "Key YmFsZGVjYXNoOnR0UENiejZKdVlSbmRGRlFwemdp"
PAGE_SIZE = 100
CUTOFF = datetime(2026, 6, 24)

SENDERS = [
    "jose@patiodigital.pe",
    "meylin.miyashiro@baldecash.com",
    "antonio@bichopublicidad.com",
    "cecilia.aliaga@baldecash.com"
]

# 6 months back from now
DATE_FROM = "2025-12-24T00:00:00.000Z"

MONTH_MAP = {
    (2026, 1): "ene", (2026, 2): "feb", (2026, 3): "mar",
    (2026, 4): "abr", (2026, 5): "may", (2026, 6): "jun"
}
MONTH_IDX = {"ene": 3, "feb": 4, "mar": 5, "abr": 6, "may": 7, "jun": 8}

def api_call(uri):
    """Make a Blip API call"""
    body = json.dumps({
        "id": f"ac-{int(time.time()*1000)}",
        "to": "postmaster@activecampaign.msging.net",
        "method": "get",
        "uri": uri
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": AUTH_KEY
    })
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read())
            if data.get("status") == "success":
                return data.get("resource", {})
            return {}
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  ERROR: {e}")
                return {}

def fetch_campaigns_for_sender(sender):
    """Fetch all campaigns for a sender with pagination"""
    campaigns = []
    skip = 0
    while True:
        uri = (f"/campaigns/summaries?created={DATE_FROM}"
               f"&CampaignSender={urllib.request.quote(sender)}"
               f"&$skip={skip}&$take={PAGE_SIZE}")
        result = api_call(uri)
        items = result.get("items", [])
        if not items:
            break
        campaigns.extend(items)
        print(f"    skip={skip}, got {len(items)} campaigns")
        skip += PAGE_SIZE
        time.sleep(0.5)
    return campaigns

# ============================================================
# 1. FETCH ALL CAMPAIGNS
# ============================================================
print("=" * 60)
print("FETCHING ACTIVE CAMPAIGN DATA FROM BLIP API")
print("=" * 60)

all_campaigns = []
for sender in SENDERS:
    print(f"\n  Sender: {sender}")
    campaigns = fetch_campaigns_for_sender(sender)
    print(f"  -> {len(campaigns)} campaigns")
    all_campaigns.extend(campaigns)

print(f"\nTotal campaigns: {len(all_campaigns)}")

# ============================================================
# 2. PROCESS: extract template, month, recipients
# ============================================================
print("\nProcessing campaigns...")

tpl_month_count = defaultdict(lambda: defaultdict(int))
tpl_month_phones = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
phone_month_count = defaultdict(lambda: defaultdict(int))
total_records = 0
skipped = 0

for camp in all_campaigns:
    tpl = camp.get("messageTemplate", "")
    send_date_str = camp.get("sendDate", "")
    if not tpl or not send_date_str:
        skipped += 1
        continue

    # Parse date (strip timezone for comparison)
    try:
        sd = datetime.strptime(send_date_str[:19], "%Y-%m-%dT%H:%M:%S")
    except:
        skipped += 1
        continue

    if sd >= CUTOFF:
        skipped += 1
        continue

    ym = (sd.year, sd.month)
    month = MONTH_MAP.get(ym)
    if not month:
        skipped += 1
        continue

    # Count recipients from statusAudience
    audience = camp.get("statusAudience", [])
    if not audience:
        # Campaign with no audience data - count as 1
        tpl_month_count[tpl][month] += 1
        total_records += 1
        continue

    for recipient in audience:
        identity = recipient.get("recipientIdentity", "")
        phone = identity.split("@")[0] if identity else ""
        tpl_month_count[tpl][month] += 1
        if phone:
            tpl_month_phones[tpl][month][phone] += 1
            phone_month_count[phone][month] += 1
        total_records += 1

print(f"Total records: {total_records:,}")
print(f"Skipped: {skipped}")
print(f"Unique templates: {len(tpl_month_count)}")

# Show per-month totals
month_totals = defaultdict(int)
for tpl, months in tpl_month_count.items():
    for m, cnt in months.items():
        month_totals[m] += cnt
for m in ["ene", "feb", "mar", "abr", "may", "jun"]:
    print(f"  {m}: {month_totals.get(m, 0):,}")

# ============================================================
# 3. UPDATE JS FILES (same logic as incorporate_ac.py)
# ============================================================
print("\n" + "=" * 60)
print("UPDATING JS FILES")
print("=" * 60)

# --- template_data.js ---
print("\n1. Updating template_data.js...")
with open("template_data.js", "r", encoding="utf-8") as f:
    raw = f.read()
prefix = "const templateData = "
data = json.loads(raw[len(prefix):].rstrip().rstrip(";"))

existing = {}
for i, row in enumerate(data):
    key = (row[0], row[1])
    existing[key] = i

added = 0
for tpl, months in tpl_month_count.items():
    key = ("blip", tpl)
    if key in existing:
        # Template already exists — AC data might add to it
        # But we follow the original incorporate_ac.py logic: skip existing
        continue
    row = ["blip", tpl, "retargeting",
           months.get("ene", 0), months.get("feb", 0), months.get("mar", 0),
           months.get("abr", 0), months.get("may", 0), months.get("jun", 0),
           0, "MARKETING"]
    row[9] = sum(row[3:9])
    if row[9] > 0:
        data.append(row)
        added += 1

data.sort(key=lambda x: -x[9])
with open("template_data.js", "w", encoding="utf-8") as f:
    f.write(prefix + json.dumps(data, ensure_ascii=False) + ";")
print(f"  Added {added} AC retargeting templates. Total: {len(data)}")

# --- template_totals.js ---
print("\n2. Updating template_totals.js...")
totals = {}
for m in ["ene", "feb", "mar", "abr", "may", "jun"]:
    idx = MONTH_IDX[m]
    by_area = defaultdict(int)
    by_meta = defaultdict(int)
    grand = 0
    for row in data:
        v = row[idx]
        if v > 0:
            by_area[row[2]] += v
            by_meta[row[10]] += v
            grand += v
    totals[m] = {"grand": grand, "byArea": dict(by_area), "byMeta": dict(by_meta)}

with open("template_totals.js", "w", encoding="utf-8") as f:
    f.write("const templateTotals = " + json.dumps(totals, ensure_ascii=False) + ";")
for m in ["ene", "feb", "mar", "abr", "may", "jun"]:
    retarg = totals[m]["byArea"].get("retargeting", 0)
    grand = totals[m]["grand"]
    print(f"  {m}: grand={grand:,}  retargeting={retarg:,}")

# --- phone_inline.js ---
print("\n3. Updating phone_inline.js...")
with open("phone_inline.js", "r", encoding="utf-8") as f:
    raw = f.read()
phone_data = json.loads(raw[len("const allPhoneData = "):].rstrip().rstrip(";"))

for month_key in ["ene", "feb", "mar", "abr", "may", "jun"]:
    current = {row[0]: list(row) for row in phone_data.get(month_key, [])}
    ac_added = 0
    for phone, months in phone_month_count.items():
        cnt = months.get(month_key, 0)
        if cnt == 0:
            continue
        if phone in current:
            current[phone][1] += cnt
        else:
            current[phone] = [phone, cnt, 0]
            ac_added += 1
    phone_data[month_key] = sorted(current.values(), key=lambda x: -x[1])
    print(f"  {month_key}: {len(phone_data[month_key]):,} phones (+{ac_added} new from AC)")

with open("phone_inline.js", "w", encoding="utf-8") as f:
    f.write("const allPhoneData = " + json.dumps(phone_data, ensure_ascii=False) + ";")

# --- template_phones.js ---
print("\n4. Updating template_phones.js...")
with open("template_phones.js", "r", encoding="utf-8") as f:
    raw = f.read()
tpl_phones = json.loads(raw[len("const templatePhones = "):].rstrip().rstrip(";"))

for month_key in ["ene", "feb", "mar", "abr", "may", "jun"]:
    if month_key not in tpl_phones:
        tpl_phones[month_key] = {}
    ac_tpls_added = 0
    for tpl, months in tpl_month_phones.items():
        if month_key not in months:
            continue
        phones = months[month_key]
        key = ("blip", tpl)
        if key not in existing:
            phone_list = sorted([[p, c] for p, c in phones.items()], key=lambda x: -x[1])
            tpl_phones[month_key][tpl] = phone_list
            ac_tpls_added += 1
    print(f"  {month_key}: {len(tpl_phones[month_key])} templates (+{ac_tpls_added} AC)")

with open("template_phones.js", "w", encoding="utf-8") as f:
    f.write("const templatePhones = " + json.dumps(tpl_phones, ensure_ascii=False) + ";")

print("\n=== DONE ===")
