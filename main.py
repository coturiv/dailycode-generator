import os
import sys
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import requests
    

def pick_idea(seed, ideas):
    if not ideas:
        return "idea"
    h = hashlib.sha256(seed.encode()).hexdigest()
    idx = int(h[:8], 16) % len(ideas)
    return ideas[idx]

def slugify(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "idea"

def hf_generate(prompt, model, token):
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {"Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 600,
            "temperature": 0.7,
            "do_sample": True,
            "return_full_text": False
        }
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        if isinstance(item, dict) and "generated_text" in item:
            return item["generated_text"]
        if isinstance(item, str):
            return item
    if isinstance(data, dict):
        if "generated_text" in data:
            return data["generated_text"]
        if "error" in data:
            return None
    return None

def hf_generate_first(prompt, models, token):
    for m in models:
        if not m:
            continue
        t = hf_generate(prompt, m, token)
        if t:
            return t
    return None

def ollama_generate(prompt, model):
    try:
        url = "http://localhost:11434/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code != 200:
            return None
        d = r.json()
        return d.get("response") or None
    except Exception:
        return None

def strip_code_fences(text):
    if text is None:
        return None
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    return text.strip()

def fallback_code(idea):
    base = (
        "# compact fallback implementation when AI code is unavailable\n"
        "import math\nimport random\n\n"
    )
    if "ascii" in idea or "art" in idea or "date" in idea:
        body = (
            "# generate an ascii mosaic using simple trigonometric patterns\n"
            "def generate(n=40):\n"
            "    r=[]\n"
            "    t=random.Random(n)\n"
            "    for i in range(n):\n"
            "        line=''\n"
            "        for j in range(n):\n"
            "            # blend sine and cosine fields with a random perturbation\n"
            "            x=math.sin(i*0.15)+math.cos(j*0.15)\n"
            "            y=math.sin((i+j)*0.08)\n"
            "            v=x*y+t.random()*0.5\n"
            "            # map magnitude to a small palette of characters\n"
            "            line+=(' .:+*#'[min(5,int(abs(v)*6))])\n"
            "        r.append(line)\n"
            "    sep='\\n'\n"
            "    return sep.join(r)\n\n"
            "if __name__=='__main__':\n"
            "    print(generate())\n"
        )
        return base + body
    body = (
        "# compute partial sums of the alternating harmonic series\n"
        "def series(k=256):\n"
        "    t=0.0\n"
        "    a=[]\n"
        "    for i in range(1,k):\n"
        "        # add (+/-) 1/i depending on parity to build the series\n"
        "        t+=((-1)**(i+1))*(1.0/i)\n"
        "        a.append(t)\n"
        "    return a\n\n"
        "if __name__=='__main__':\n"
        "    s=series()\n"
        "    # show length and final approximation\n"
        "    print(len(s),round(s[-1],6))\n"
    )
    return base + body

def fetch_weather(lat, lon, date_str):
    def wmo_condition(code):
        if code is None:
            return "unknown"
        if code in (0, 1):
            return "sunny"
        if code in (2, 3):
            return "clouds"
        if code in (45, 48):
            return "fog"
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            return "rain"
        if code in (71, 73, 75, 77, 85, 86):
            return "snow"
        if code in (95, 96, 99):
            return "thunderstorm"
        return "unknown"
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast?latitude=" + str(lat) +
            "&longitude=" + str(lon) +
            "&daily=weathercode,precipitation_sum" +
            "&start_date=" + date_str + "&end_date=" + date_str + "&timezone=UTC"
        )
        r = requests.get(url, timeout=30)
        d = r.json()
        daily = d.get("daily", {})
        code = daily.get("weathercode", [None])[0]
        return wmo_condition(code)
    except Exception:
        return "unknown"

def fetch_holidays_global(date_str):
    try:
        url = "https://date.nager.at/api/v3/NextPublicHolidaysWorldwide"
        r = requests.get(url, timeout=30)
        arr = r.json()
        names = [x.get("name") for x in arr if x.get("date") == date_str]
        return ", ".join([n for n in names if n]) or "none"
    except Exception:
        return "none"

def fetch_trending(lang, y, m, d):
    try:
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{y}/{m}/{d}"
        r = requests.get(url, timeout=30)
        data = r.json()
        items = data.get("items", [])
        if not items:
            return []
        arts = items[0].get("articles", [])
        titles = [a.get("article") for a in arts if a.get("article") and a.get("article") != "Main_Page"]
        return titles[:5]
    except Exception:
        return []

def local_ideas(ctx):
    date = ctx.get("date", "")
    weather = (ctx.get("weather") or "unknown").lower()
    holidays = ctx.get("holidays") or "none"
    topics = ctx.get("topics") or []
    base = [
        "ninja " + weather + " data pipeline",
        "ninja holiday scheduler: " + holidays,
        "ninja trending analyzer: " + (", ".join(topics[:2]) if topics else "none"),
        "ninja date cipher: " + date,
        "ninja event stream aggregator",
        "ninja graph walk under " + weather,
        "ninja robust parsing toolkit",
        "ninja text sampler with trending bias",
        "ninja time-series sketch from weather",
        "ninja holiday-aware calendar utils",
    ]
    return [x for x in base if x]

def refresh_ideas(model, token, now):
    if not token:
        date_str = now.strftime("%Y-%m-%d")
        y = now.strftime("%Y")
        m = now.strftime("%m")
        d = now.strftime("%d")
        lat = float(os.environ.get("LOCATION_LAT", "51.5074"))
        lon = float(os.environ.get("LOCATION_LON", "-0.1278"))
        lang = os.environ.get("WIKI_LANG", "en")
        weather = fetch_weather(lat, lon, date_str)
        holidays = fetch_holidays_global(date_str)
        topics = fetch_trending(lang, y, m, d)
        ctx = {"date": date_str, "weather": weather, "holidays": holidays, "topics": topics}
        return local_ideas(ctx), ctx
    date_str = now.strftime("%Y-%m-%d")
    y = now.strftime("%Y")
    m = now.strftime("%m")
    d = now.strftime("%d")
    lat = float(os.environ.get("LOCATION_LAT", "51.5074"))
    lon = float(os.environ.get("LOCATION_LON", "-0.1278"))
    lang = os.environ.get("WIKI_LANG", "en")
    weather = fetch_weather(lat, lon, date_str)
    holidays = fetch_holidays_global(date_str)
    topics = fetch_trending(lang, y, m, d)
    ctx = {
        "date": date_str,
        "weather": weather,
        "holidays": holidays,
        "topics": topics,
    }
    prompt = (
        "Generate 10 concise 'ninja' learning ideas as plain lines. "
        "Use date, weather, public holidays, and trending topics. "
        "Date: " + ctx["date"] + 
        "; Weather: " + ctx["weather"] + 
        "; Holidays: " + ctx["holidays"] + 
        "; Topics: " + ", ".join(ctx["topics"]) + 
        ". Only output the ideas, one per line."
    )
    ollama_model = os.environ.get("OLLAMA_MODEL", "")
    text = None
    if ollama_model:
        text = ollama_generate(prompt, ollama_model)
    if not text:
        candidates = []
        if model:
            candidates.append(model)
        candidates.extend(["bigcode/starcoder2-1b", "HuggingFaceH4/zephyr-7b-beta"])
        seen = set()
        models = []
        for m2 in candidates:
            if m2 and m2 not in seen:
                models.append(m2)
                seen.add(m2)
        text = hf_generate_first(prompt, models, token)
    if not text:
        return local_ideas(ctx), ctx
    text = strip_code_fences(text)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return lines, ctx

def update_readme_latest_idea(idea, date_str, ctx):
    p = Path("README.md")
    try:
        content = p.read_text(encoding="utf-8")
    except Exception:
        return
    lines = content.splitlines()
    replaced = False
    context_line = (
        "Context: weather=" + str(ctx.get("weather", "unknown")) +
        "; holidays=" + (ctx.get("holidays", "none") or "none") +
        "; topics=" + (", ".join(ctx.get("topics", [])) if ctx.get("topics") else "none")
    )
    for i, ln in enumerate(lines):
        if ln.startswith("Latest idea (UTC):"):
            lines[i] = "Latest idea (UTC): " + date_str + " — " + idea
            replaced = True
            if i + 1 < len(lines) and lines[i+1].startswith("Context:"):
                lines[i+1] = context_line
            else:
                lines.insert(i+1, context_line)
            break
    if not replaced:
        for i, ln in enumerate(lines):
            if ln.startswith("# "):
                lines.insert(i+1, "Latest idea (UTC): " + date_str + " — " + idea)
                lines.insert(i+2, context_line)
                replaced = True
                break
    if not replaced:
        lines.append("Latest idea (UTC): " + date_str + " — " + idea)
        lines.append(context_line)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

def build_prompt(idea):
    return (
        "Generate a concise Python 'ninja' learning script with clear, brief comments. "
        "Make it clever but accessible, showcasing a non-trivial concept. "
        "Implement a self-contained program for: "
        + idea + 
        ". Use only the standard library and include a main entry point."
    )

def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    def load_env_file(path=".env"):
        p = Path(path)
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
        for ln in lines:
            s = ln.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:
                os.environ[k] = v
    load_env_file()
    model = os.environ.get("HF_MODEL", "bigcode/starcoder2-3b")
    token = os.environ.get("HF_TOKEN", "")
    ideas, ctx = refresh_ideas(model, token, now)
    if not ideas:
        print(json.dumps({"error": "ideas refresh failed", "date": date_str}))
        sys.exit(1)
    idea = pick_idea(date_str, ideas)
    update_readme_latest_idea(idea, date_str, ctx)
    slug = slugify(idea)
    out_dir = Path("generated") / now.strftime("%Y") / now.strftime("%m")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date_str}_{slug}.py"
    prompt = build_prompt(idea)
    code = None
    if token:
        ollama_model = os.environ.get("OLLAMA_MODEL", "")
        if ollama_model:
            code = ollama_generate(prompt, ollama_model)
        if not code:
            code = hf_generate_first(prompt, [model, "bigcode/starcoder2-1b", "HuggingFaceH4/zephyr-7b-beta"], token)
    if not code:
        code = fallback_code(idea)
    code = strip_code_fences(code)
    header = f"# idea: {idea}\n"
    Path(out_file).write_text(header + code, encoding="utf-8")
    try:
        import subprocess
        msg = f"chore(ninja): add {date_str} {idea}"
        subprocess.run(["git", "add", str(out_file)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        author_name = os.environ.get("COMMIT_AUTHOR_NAME", "")
        author_email = os.environ.get("COMMIT_AUTHOR_EMAIL", "")
        if author_name and author_email:
            cmd = ["git", "-c", f"user.name={author_name}", "-c", f"user.email={author_email}", "commit", "-m", msg]
        else:
            cmd = ["git", "commit", "-m", msg]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print(json.dumps({"file": str(out_file), "idea": idea, "model": model}))

if __name__ == "__main__":
    main()