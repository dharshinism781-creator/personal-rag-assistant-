import json, os, re
from datetime import date, datetime

TIMELINE_FILE = "timeline.json"

def extract_dates(client, text, filename):
    prompt = f"""Find important dates (expiry, renewal, due, deadline, exam) in the text.
Return ONLY a JSON list like [{{"label": "Passport expiry", "date": "YYYY-MM-DD"}}].
If none, return [].

Text:
{text[:6000]}"""
    r = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = r.choices[0].message.content or ""
    m = re.search(r"\[.*\]", raw, re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except Exception:
        items = []

    saved = _load()
    for it in items:
        if "date" in it and "label" in it:
            saved.append({"label": it["label"], "date": it["date"], "source": filename})
    with open(TIMELINE_FILE, "w") as f:
        json.dump(saved, f)
    return items

def _load():
    if os.path.exists(TIMELINE_FILE):
        with open(TIMELINE_FILE) as f:
            return json.load(f)
    return []

def get_timeline():
    out = []
    for it in _load():
        try:
            d = datetime.strptime(it["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        days = (d - date.today()).days
        status = "expired" if days < 0 else "urgent" if days <= 30 else "upcoming"
        out.append({**it, "days_left": days, "status": status})
    return sorted(out, key=lambda x: x["days_left"])