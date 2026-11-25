#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_icons.py - fetch mainstream OSS icon libraries from jsDelivr.

Discipline (hard requirements):
  - global request spacing >= 200ms (single global rate limiter)
  - global concurrency <= 3 (thread pool with 3 workers)
  - 3 retries per failed request with backoff (extra slow-backoff on 429/403)
  - resumable: existing non-empty files are skipped
  - SVG bytes are stored verbatim, never rewritten
"""
import concurrent.futures as cf
import datetime
import http.client
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ICONS_ROOT = r"C:\Users\admin\.claude\skills\design-system-generator\data\icons"
COLLECTOR_DIR = os.path.join(ICONS_ROOT, "_collector")
TREES_DIR = os.path.join(COLLECTOR_DIR, "trees")
FAILED_DIR = os.path.join(COLLECTOR_DIR, "failed")
LOG_PATH = os.path.join(COLLECTOR_DIR, "collect.log")

FILE_INTERVAL = 0.205     # seconds between file-download request starts (global)
API_INTERVAL = 1.0        # data.jsdelivr.com calls get a gentler pace
MAX_WORKERS = 3
RETRIES = 3               # retries after the first failure => up to 4 attempts
SIZE_BUDGET = 60 * 1024 * 1024   # per-library full-download budget
SAMPLE_PER_FORM = 800

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) design-system-icon-collector/1.0",
    "Accept": "*/*",
}

LOCK = threading.Lock()
LOG_FH = None


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    with LOCK:
        try:
            print(line, flush=True)
        except Exception:
            pass
        if LOG_FH:
            try:
                LOG_FH.write(line + "\n")
                LOG_FH.flush()
            except Exception:
                pass


def F(prefix, out, label, suffix=None, exclude=None, keep_subpath=False):
    """Form config: package path prefix -> output subdir under lib dir."""
    return {"prefix": prefix, "out": out, "label": label, "suffix": suffix,
            "exclude": exclude, "keepSubPath": keep_subpath}


LIBS = [
    {
        "name": "tabler", "license": "MIT",
        "source": "npm:@tabler/icons",
        "packages": [("npm", "@tabler/icons", [
            F("icons/outline/", "outline", "线性"),
            F("icons/filled/", "filled", "面性"),
        ])],
    },
    {
        "name": "phosphor", "license": "MIT",
        "source": "npm:@phosphor-icons/core",
        "packages": [("npm", "@phosphor-icons/core", [
            F("assets/regular/", "regular", "线性"),
            F("assets/fill/", "fill", "面性"),
        ])],
    },
    {
        "name": "heroicons", "license": "MIT",
        "source": "gh:tailwindlabs/heroicons@master",
        "packages": [("gh", "tailwindlabs/heroicons@master", [
            F("optimized/24/outline/", "outline-24", "线性"),
            F("optimized/24/solid/", "solid-24", "面性"),
            F("optimized/20/solid/", "solid-20", "面性20"),
        ])],
    },
    {
        "name": "material-symbols", "license": "Apache-2.0",
        "source": "npm:@material-symbols/svg-400 (outlined/ 内含 -fill 面性变体)",
        "packages": [
            ("npm", "@material-symbols/svg-400", [
                # package layout: {outlined,rounded,sharp}/{<name>.svg,<name>-fill.svg}
                F("outlined/", "outlined", "线性", exclude="-fill.svg"),
                F("outlined/", "filled", "面性", suffix="-fill.svg"),
            ]),
        ],
    },
    {
        "name": "bootstrap", "license": "MIT",
        "source": "npm:bootstrap-icons",
        "packages": [("npm", "bootstrap-icons", [F("icons/", "", "线性(填充路径)")])],
    },
    {
        "name": "remixicon", "license": "Apache-2.0",
        "source": "npm:remixicon",
        # actual package layout is icons/<Category>/<name>-line.svg / -fill.svg
        # so we match by filename suffix across icons/ and flatten into line/ fill/
        "packages": [("npm", "remixicon", [
            F("icons/", "line", "线性", suffix="-line.svg"),
            F("icons/", "fill", "面性", suffix="-fill.svg"),
        ])],
    },
    {
        "name": "feather", "license": "MIT",
        "source": "npm:feather-icons",
        "packages": [("npm", "feather-icons", [F("dist/icons/", "", "线性")])],
    },
    {
        "name": "boxicons", "license": "CC-4.0",
        "source": "npm:boxicons",
        "packages": [("npm", "boxicons", [
            F("svg/regular/", "regular", "线性"),
            F("svg/solid/", "solid", "面性"),
        ])],
    },
    {
        "name": "solar", "license": "CC-BY-4.0",
        "source": "gh:480-Design/Solar-icon-set@main",
        # layout: icons/SVG/{Outline,Linear,Line Duotone,Bold,Bold Duotone,Broken}/<Category>/*.svg
        "packages": [("gh", "480-Design/Solar-icon-set@main", [
            F("icons/SVG/Linear/", "linear", "线性", keep_subpath=True),
            F("icons/SVG/Bold/", "bold", "面性", keep_subpath=True),
        ])],
    },
]


class Limiter(object):
    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_time = 0.0
        self.penalty = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(self.next_time, now)
            self.next_time = t + self.interval + self.penalty
        d = t - now
        if d > 0:
            time.sleep(d)

    def penalize(self, amount):
        with self.lock:
            self.penalty = min(self.penalty + amount, 0.6)


FILE_LIMITER = Limiter(FILE_INTERVAL)
API_LIMITER = Limiter(API_INTERVAL)


def http_get(url, limiter, attempts=1 + RETRIES):
    last = None
    for i in range(attempts):
        limiter.wait()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = "HTTP %s" % e.code
            if e.code in (429, 403):
                limiter.penalize(0.1)
                time.sleep(min(30 * (i + 1), 90))
            else:
                time.sleep(2 * (i + 1))
        except Exception as e:
            last = str(e)
            time.sleep(2 * (i + 1))
    raise RuntimeError("GET failed after %d attempts: %s (%s)" % (attempts, url, last))


def sanitize(key):
    return re.sub(r"[^A-Za-z0-9._-]", "_", key)


def tree_url(kind, ident):
    # ident already carries an explicit resolved version/tag (never @latest)
    return "https://data.jsdelivr.com/v1/packages/%s/%s?structure=flat" % (kind, ident)


def save_tree(kind, ident, data):
    os.makedirs(TREES_DIR, exist_ok=True)
    path = os.path.join(TREES_DIR, sanitize(kind + "_" + ident) + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def has_version(ident):
    # "@tabler/icons" (scoped, no version) -> last segment "icons" has no @
    return "@" in ident.rsplit("/", 1)[-1]


def resolve_latest(kind, ident):
    """jsDelivr data API no longer resolves @latest / npm tags: ask /resolved."""
    bare = ident.split("@")[0] if kind == "gh" else ident
    os.makedirs(TREES_DIR, exist_ok=True)
    path = os.path.join(TREES_DIR, "resolved_" + sanitize(kind + "_" + bare) + ".json")
    if os.path.exists(path) and os.path.getsize(path) > 2:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh).get("version")
    url = "https://data.jsdelivr.com/v1/packages/%s/%s/resolved?specifier=latest" % (kind, bare)
    raw = http_get(url, API_LIMITER)
    data = json.loads(raw.decode("utf-8", "replace"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data.get("version")


def load_tree(kind, ident):
    os.makedirs(TREES_DIR, exist_ok=True)
    cache = os.path.join(TREES_DIR, sanitize(kind + "_" + ident) + ".json")
    if os.path.exists(cache) and os.path.getsize(cache) > 2:
        with open(cache, "r", encoding="utf-8") as fh:
            return json.load(fh)
    use_ident = ident
    if not has_version(ident):
        if kind == "npm":
            v = resolve_latest(kind, ident)
            if not v:
                raise RuntimeError("cannot resolve latest version for npm %s" % ident)
            use_ident = ident + "@" + v
    try:
        raw = http_get(tree_url(kind, use_ident), API_LIMITER)
    except RuntimeError:
        if kind == "gh" and "@" in use_ident:
            # branch/tag guess failed -> resolve latest release tag
            v = resolve_latest(kind, use_ident.split("@")[0])
            if not v:
                raise
            use_ident = use_ident.split("@")[0] + "@" + v
            raw = http_get(tree_url(kind, use_ident), API_LIMITER)
        else:
            raise
    data = json.loads(raw.decode("utf-8", "replace"))
    save_tree(kind, use_ident, data)
    if use_ident != ident:
        save_tree(kind, ident, data)
    return data


def iter_svg(tree):
    for f in tree.get("files", []):
        if f.get("type") == "directory":
            continue
        name = (f.get("name") or "").lstrip("/")
        if name.lower().endswith(".svg"):
            yield name, int(f.get("size") or 0)


def select_files(tree, form):
    prefix = form["prefix"]
    suffix = form.get("suffix")
    exclude = form.get("exclude")
    out = []
    for name, size in iter_svg(tree):
        if not name.startswith(prefix):
            continue
        if suffix is not None and not name.endswith(suffix):
            continue
        if exclude is not None and name.endswith(exclude):
            continue
        out.append((name, size))
    out.sort(key=lambda x: x[0].rsplit("/", 1)[-1].lower())
    return out


def dir_histogram(tree, max_rows=25):
    counts = {}
    for name, _size in iter_svg(tree):
        parts = name.split("/")
        key = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
        counts[key] = counts.get(key, 0) + 1
    rows = sorted(counts.items(), key=lambda x: -x[1])[:max_rows]
    return rows


def resolve_version(kind, ident, tree):
    version = tree.get("version")
    if version:
        return str(version)
    if kind == "npm":
        return "latest"
    return ident.split("@")[-1] or "master"


def build_lib_plan(lib, verbose=False):
    """Returns (plan, problems). plan: list of packages with resolved forms."""
    problems = []
    plan = {"name": lib["name"], "packages": [], "sampled": False, "fullTotal": 0}
    all_forms = []  # (pkg_kind, pkg_ident, version, form, [(name,size)...])
    for kind, ident, forms in lib["packages"]:
        try:
            tree = load_tree(kind, ident)
        except Exception as e:
            problems.append("tree fetch failed for %s %s: %s" % (kind, ident, e))
            continue
        version = resolve_version(kind, ident, tree)
        if not forms:
            rows = dir_histogram(tree)
            log("[%s] NO FORMS CONFIGURED - svg dir histogram for %s %s:" % (lib["name"], kind, ident))
            for k, c in rows:
                log("    %5d  %s" % (c, k if k else "(root)"))
            total = sum(1 for _ in iter_svg(tree))
            log("[%s] total svg files in package: %d" % (lib["name"], total))
            problems.append("forms not configured for %s" % ident)
            continue
        for form in forms:
            sel = select_files(tree, form)
            if not sel:
                rows = dir_histogram(tree, 15)
                problems.append("%s %s: form prefix '%s' matched 0 files" % (kind, ident, form["prefix"]))
                log("[%s] form '%s' matched 0 svgs. histogram:" % (lib["name"], form["out"]))
                for k, c in rows:
                    log("    %5d  %s" % (c, k if k else "(root)"))
                continue
            if verbose:
                log("[%s] form %-12s prefix=%-28s files=%d bytes=%d (first: %s)" % (
                    lib["name"], form["out"] or "(flat)", form["prefix"], len(sel),
                    sum(s for _, s in sel), sel[0][0]))
            all_forms.append((kind, ident, version, form, sel))
    if not all_forms:
        return plan, problems
    total_full = sum(len(sel) for _, _, _, _, sel in all_forms)
    total_bytes = sum(s for _, _, _, _, sel in all_forms for _, s in sel)
    plan["fullTotal"] = total_full
    if total_bytes > SIZE_BUDGET:
        plan["sampled"] = True
        log("[%s] full size %.1f MB > %.0f MB budget => SAMPLE first %d per form (sorted by filename)"
            % (lib["name"], total_bytes / 1048576.0, SIZE_BUDGET / 1048576.0, SAMPLE_PER_FORM))
        all_forms = [(k, i, v, f, sel[:SAMPLE_PER_FORM]) for k, i, v, f, sel in all_forms]
    pkg_map = {}
    for kind, ident, version, form, sel in all_forms:
        key = (kind, ident, version)
        if key not in pkg_map:
            pkg_map[key] = {"kind": kind, "ident": ident, "version": version, "forms": []}
        pkg_map[key]["forms"].append({"form": form, "files": sel})
    plan["packages"] = list(pkg_map.values())
    return plan, problems


class Stats(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.done = 0
        self.skipped = 0
        self.bytes = 0
        self.failed = []

    def ok(self, nbytes):
        with self.lock:
            self.done += 1
            self.bytes += nbytes

    def skip(self):
        with self.lock:
            self.skipped += 1

    def fail(self, rec):
        with self.lock:
            self.failed.append(rec)


_TLS = threading.local()

# jsDelivr official edges; cdn.jsdelivr.net gets network-reset in some regions,
# fastly/gcore serve identical content and are tried in order on connection errors
CDN_HOSTS = ["cdn.jsdelivr.net", "fastly.jsdelivr.net", "gcore.jsdelivr.net"]
_HOST_LOCK = threading.Lock()
_HOST_IDX = 0


def current_host():
    with _HOST_LOCK:
        return CDN_HOSTS[_HOST_IDX % len(CDN_HOSTS)]


def rotate_host(dead):
    global _HOST_IDX
    with _HOST_LOCK:
        if CDN_HOSTS[_HOST_IDX % len(CDN_HOSTS)] == dead:
            _HOST_IDX += 1
            log("CDN host %s unreachable -> switching to %s"
                % (dead, CDN_HOSTS[_HOST_IDX % len(CDN_HOSTS)]))


def fetch_keepalive(path):
    """GET https://<jsdelivr edge><path> reusing a per-thread connection.

    Returns (data, status, location). Raises on transport errors, rotates
    to the next official edge and resets the connection for the next attempt.
    """
    host = current_host()
    conn = getattr(_TLS, "conn", None)
    thost = getattr(_TLS, "host", None)
    if conn is None or thost != host:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        conn = http.client.HTTPSConnection(host, timeout=30)
        _TLS.conn = conn
        _TLS.host = host
    try:
        conn.request("GET", path, headers=HEADERS)
        r = conn.getresponse()
        data = r.read()
        loc = r.getheader("Location") if r.status in (301, 302, 303, 307, 308) else None
        return data, r.status, loc
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        _TLS.conn = None
        rotate_host(host)
        raise


def download_one(limiter, url, target, stats):
    if os.path.exists(target) and os.path.getsize(target) > 0:
        stats.skip()
        return True
    path = urllib.parse.urlsplit(url).path
    last = None
    for attempt in range(1 + RETRIES):
        limiter.wait()
        try:
            data, status, loc = fetch_keepalive(path)
            if status in (301, 302, 303, 307, 308):
                # rare (should not happen with pinned versions) -> follow via urllib
                data = http_get(loc if loc and loc.startswith("http") else
                                "https://%s%s" % (current_host(), loc or path), limiter)
            elif status != 200:
                raise urllib.error.HTTPError(url, status, "HTTP %s" % status, None, None)
            if len(data) < 15 or b"<svg" not in data:
                raise ValueError("content is not SVG (len=%d)" % len(data))
            tmp = target + ".part"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, target)
            stats.ok(len(data))
            return True
        except urllib.error.HTTPError as e:
            last = "HTTP %s" % e.code
            if e.code in (429, 403):
                limiter.penalize(0.1)
                time.sleep(min(30 * (attempt + 1), 90))
            elif e.code == 404 and attempt >= 1:
                break  # a missing file will not appear on retry
            else:
                time.sleep(2 * (attempt + 1))
        except Exception as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
    stats.fail({"url": url, "target": target, "error": last})
    return False


def form_out_dir(lib_name, form):
    d = os.path.join(ICONS_ROOT, lib_name, form["out"]) if form["out"] else os.path.join(ICONS_ROOT, lib_name)
    os.makedirs(d, exist_ok=True)
    return d


def collect_lib(lib, plan):
    stats = Stats()
    jobs = []
    for pkg in plan["packages"]:
        if pkg["kind"] == "npm":
            base = "https://cdn.jsdelivr.net/npm/%s@%s/" % (pkg["ident"], pkg["version"])
        else:
            user_repo = pkg["ident"].split("@")[0]
            base = "https://cdn.jsdelivr.net/gh/%s@%s/" % (user_repo, pkg["version"])
        for entry in pkg["forms"]:
            form = entry["form"]
            outdir = form_out_dir(lib["name"], form)
            for name, _size in entry["files"]:
                if form.get("keepSubPath"):
                    # keep the package's own sub-structure under the form dir
                    # (solar: same basename means DIFFERENT icons per category)
                    rel = name[len(form["prefix"]):].replace("/", os.sep)
                    target = os.path.join(outdir, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                else:
                    basename = name.rsplit("/", 1)[-1]
                    target = os.path.join(outdir, basename)
                jobs.append((base + urllib.parse.quote(name), target))
    # safety: dedupe identical targets (first occurrence wins)
    seen = {}
    unique_jobs = []
    for url, target in jobs:
        key = target.lower()
        if key in seen:
            continue
        seen[key] = url
        unique_jobs.append((url, target))
    if len(unique_jobs) < len(jobs):
        log("[%s] WARNING: dropped %d duplicate targets" % (lib["name"], len(jobs) - len(unique_jobs)))
    jobs = unique_jobs
    total = len(jobs)
    log("[%s] downloading %d files (%d already existed will be skipped) ..."
        % (lib["name"], total, sum(1 for _, t in jobs if os.path.exists(t))))
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(download_one, FILE_LIMITER, u, t, stats) for u, t in jobs]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            if i % 250 == 0 or i == total:
                dt = max(time.time() - t0, 0.001)
                rate = stats.done / dt
                remain = (total - i) / max(rate, 0.01)
                log("[%s] %d/%d done=%d skip=%d fail=%d | %.2f req/s | ETA %02d:%02d:%02d" % (
                    lib["name"], i, total, stats.done, stats.skipped, len(stats.failed),
                    rate, int(remain // 3600), int(remain % 3600 // 60), int(remain % 60)))
    if stats.failed:
        os.makedirs(FAILED_DIR, exist_ok=True)
        fpath = os.path.join(FAILED_DIR, sanitize(lib["name"]) + ".json")
        with open(fpath, "w", encoding="utf-8") as fh:
            json.dump(stats.failed, fh, ensure_ascii=False, indent=1)
        log("[%s] FAILED downloads: %d (list saved to %s) - rerun 'download' to retry"
            % (lib["name"], len(stats.failed), fpath))
    return stats


def disk_usage(path, exclude_meta=True):
    """Count/size SVG assets only (metadata json files are not icon assets)."""
    total = 0
    count = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            if not fn.lower().endswith(".svg"):
                continue
            total += os.path.getsize(os.path.join(root, fn))
            count += 1
    return count, total


def write_meta_and_index(plans_by_lib, extra_notes=None, only=None):
    iso = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    libs_out = []
    for lib in LIBS:
        if only and lib["name"] not in only:
            continue
        lib_dir = os.path.join(ICONS_ROOT, lib["name"])
        if not os.path.isdir(lib_dir):
            continue
        plan = plans_by_lib.get(lib["name"], {})
        forms_meta = []
        by_form = {}
        total = 0
        # discover form dirs from plan (fallback: scan lib dir)
        form_dirs = []
        for pkg in plan.get("packages", []):
            for entry in pkg["forms"]:
                form = entry["form"]
                if form["out"] not in [fd[0] for fd in form_dirs]:
                    form_dirs.append((form["out"], form["label"]))
        if not form_dirs:
            # e.g. lucide or flat libs
            form_dirs = [("", None)]
        for out_key, label in form_dirs:
            d = os.path.join(lib_dir, out_key) if out_key else lib_dir
            if not os.path.isdir(d):
                continue
            cnt, byts = disk_usage(d)
            # for flat libs, exclude files that belong to form subdirs
            if not out_key and form_dirs and form_dirs[0][0]:
                sub = set()
                for ok2, _l in form_dirs:
                    sub.add(os.path.join(lib_dir, ok2))
                cnt, byts = 0, 0
                for fn in os.listdir(lib_dir):
                    p = os.path.join(lib_dir, fn)
                    if os.path.isfile(p):
                        cnt += 1
                        byts += os.path.getsize(p)
            key = out_key if out_key else "linear"
            label = label or "线性"
            forms_meta.append({"key": key, "label": label, "path": (lib["name"] + "/" + out_key).rstrip("/")})
            by_form[key] = cnt
            total += cnt
        meta = {
            "name": lib["name"],
            "license": lib["license"],
            "forms": forms_meta,
            "total": total,
            "byForm": by_form,
            "source": lib["source"],
            "sourceUrl": "https://cdn.jsdelivr.net/",
            "fetchedAt": iso,
        }
        if plan.get("sampled"):
            meta["sampled"] = True
            meta["fullTotal"] = plan.get("fullTotal")
            meta["sampleRule"] = "full size > 60MB: first %d per form by filename" % SAMPLE_PER_FORM
        if extra_notes and lib["name"] in extra_notes:
            meta["notes"] = extra_notes[lib["name"]]
        if lib["name"] == "solar":
            meta["notes"] = ("icons keep their original category sub-directories under linear/ and bold/ "
                             "because 11 basenames (e.g. Home.svg, Star.svg) are DIFFERENT icons per "
                             "category; same-basename files are not duplicates")
        if lib["name"] == "bootstrap":
            # package keeps line and -fill variants together in icons/: report the split
            svgs = [fn for fn in os.listdir(lib_dir) if fn.endswith(".svg")]
            n_fill = sum(1 for fn in svgs if fn.endswith("-fill.svg"))
            meta["forms"] = [
                {"key": "linear", "label": "线性", "path": "bootstrap"},
                {"key": "fill", "label": "面性(-fill后缀)", "path": "bootstrap"},
            ]
            meta["byForm"] = {"linear": len(svgs) - n_fill, "fill": n_fill}
        with open(os.path.join(lib_dir, "_meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
        _c, byts = disk_usage(lib_dir)
        libs_out.append({
            "name": lib["name"], "license": lib["license"],
            "forms": meta["forms"],
            "total": total, "byForm": meta["byForm"], "bytes": byts,
            "bytesMB": round(byts / 1048576.0, 2),
            "sampled": bool(plan.get("sampled")),
            "source": lib["source"],
        })
        log("META [%s] total=%d byForm=%s bytes=%.2fMB sampled=%s"
            % (lib["name"], total, json.dumps(by_form), byts / 1048576.0, bool(plan.get("sampled"))))
    # lucide: existing collection, count only
    luc_dir = os.path.join(ICONS_ROOT, "lucide")
    if os.path.isdir(luc_dir):
        cnt, byts = disk_usage(luc_dir)
        luc_meta_path = os.path.join(luc_dir, "_meta.json")
        if not os.path.exists(luc_meta_path):
            notes = "collected before this run (source: iconify:lucide per manifest.json)"
            src = "pre-existing (iconify:lucide, earlier fetch)"
            man_path = os.path.join(luc_dir, "manifest.json")
            if os.path.exists(man_path):
                try:
                    with open(man_path, "r", encoding="utf-8") as fh:
                        man = json.load(fh)
                    if man.get("backfilledAt"):
                        notes = ("icons that failed with 429 in the original iconify fetch were "
                                 "backfilled at %s from %s" % (man["backfilledAt"], man.get("backfillSource")))
                except Exception:
                    pass
            meta = {
                "name": "lucide", "license": "ISC",
                "forms": [{"key": "linear", "label": "线性", "path": "lucide"}],
                "total": cnt, "byForm": {"linear": cnt},
                "source": src,
                "sourceUrl": "https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/",
                "fetchedAt": iso,
                "notes": notes,
            }
            with open(luc_meta_path, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=2)
        libs_out.append({
            "name": "lucide", "license": "ISC",
            "forms": [{"key": "linear", "label": "线性", "path": "lucide"}],
            "total": cnt, "byForm": {"linear": cnt}, "bytes": byts,
            "bytesMB": round(byts / 1048576.0, 2), "sampled": False,
            "source": "pre-existing (lucide-static)",
        })
        log("META [lucide] total=%d bytes=%.2fMB (pre-existing)" % (cnt, byts / 1048576.0))
    total_files = sum(l["total"] for l in libs_out)
    total_bytes = sum(l["bytes"] for l in libs_out)
    index = {
        "generatedAt": iso,
        "description": "offline icon libraries for design-system-generator (icon style step)",
        "root": ICONS_ROOT,
        "rules": {
            "perLibFullBudgetMB": SIZE_BUDGET // 1048576,
            "samplePerForm": SAMPLE_PER_FORM,
            "source": "jsDelivr (npm + gh channels)",
            "svgModified": False,
        },
        "libraries": libs_out,
        "totals": {"files": total_files, "bytes": total_bytes,
                   "bytesMB": round(total_bytes / 1048576.0, 2)},
    }
    with open(os.path.join(ICONS_ROOT, "_index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
    log("INDEX written: %d libs, %d files, %.2f MB total"
        % (len(libs_out), total_files, total_bytes / 1048576.0))


def cmd_discover():
    log("=== DISCOVERY: fetching package trees from data.jsdelivr.com ===")
    any_problems = []
    grand_files = 0
    for lib in LIBS:
        plan, problems = build_lib_plan(lib, verbose=True)
        any_problems += ["[%s] %s" % (lib["name"], p) for p in problems]
        n = sum(len(e["files"]) for p in plan["packages"] for e in p["forms"])
        grand_files += n
        log("[%s] plan: %d files to download (fullTotal=%d, sampled=%s)"
            % (lib["name"], n, plan["fullTotal"], plan["sampled"]))
    eta = grand_files / 4.8
    log("=== TOTAL files planned: %d | approx ETA at ~4.8 req/s: %02d:%02d:%02d ==="
        % (grand_files, int(eta // 3600), int(eta % 3600 // 60), int(eta % 60)))
    if any_problems:
        log("PROBLEMS:")
        for p in any_problems:
            log("  - " + p)


def slim_plan(plan):
    return {
        "sampled": plan.get("sampled", False),
        "fullTotal": plan.get("fullTotal", 0),
        "formDirs": sorted({(e["form"]["out"], e["form"]["label"])
                            for p in plan["packages"] for e in p["forms"]}),
    }


def load_slim_plans():
    path = os.path.join(COLLECTOR_DIR, "plans.json")
    if not os.path.exists(path) or os.path.getsize(path) < 2:
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        slim = json.load(fh)
    plans = {}
    for name, sp in slim.items():
        plans[name] = {
            "sampled": sp.get("sampled", False),
            "fullTotal": sp.get("fullTotal", 0),
            "packages": [{"forms": [{"form": {"out": o, "label": l}} for o, l in sp["formDirs"]]}],
        }
    return plans


def cmd_download(only=None):
    plans_by_lib = {}
    for lib in LIBS:
        if only and lib["name"] not in only:
            continue
        plan, problems = build_lib_plan(lib)
        for p in problems:
            log("[%s] PROBLEM: %s" % (lib["name"], p))
        if not plan["packages"]:
            log("[%s] no downloadable plan, skipping" % lib["name"])
            continue
        stats = collect_lib(lib, plan)
        plans_by_lib[lib["name"]] = plan
        log("[%s] DONE done=%d skipped=%d failed=%d bytes=%d"
            % (lib["name"], stats.done, stats.skipped, len(stats.failed), stats.bytes))
    slim = load_slim_plans()
    slim.update({k: slim_plan(v) for k, v in plans_by_lib.items()})
    with open(os.path.join(COLLECTOR_DIR, "plans.json"), "w", encoding="utf-8") as fh:
        json.dump(slim, fh)
    write_meta_and_index(plans_by_lib, only=only)


def cmd_meta():
    write_meta_and_index(load_slim_plans())


def cmd_fix_lucide():
    """Backfill lucide icons that failed (HTTP 429) in the earlier Iconify-based
    collection, using lucide-static from jsDelivr. Existing files are untouched."""
    luc_dir = os.path.join(ICONS_ROOT, "lucide")
    manifest_path = os.path.join(luc_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        log("[lucide] no manifest.json - nothing to backfill")
        return
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    missing = []
    for entry in manifest.get("failed", []):
        name = entry.split(":", 1)[0].strip()
        if name and not os.path.exists(os.path.join(luc_dir, name + ".svg")):
            missing.append(name)
    if not missing:
        log("[lucide] no missing icons detected")
        return
    version = resolve_latest("npm", "lucide-static")
    log("[lucide] backfilling %d missing icons from lucide-static@%s" % (len(missing), version))
    stats = Stats()
    limiter = FILE_LIMITER
    jobs = []
    for name in missing:
        path = "/npm/lucide-static@%s/icons/%s.svg" % (version, urllib.parse.quote(name))
        jobs.append(("https://cdn.jsdelivr.net" + path, os.path.join(luc_dir, name + ".svg")))
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(download_one, limiter, u, t, stats) for u, t in jobs]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            if i % 50 == 0 or i == len(jobs):
                log("[lucide] backfill %d/%d done=%d fail=%d" % (i, len(jobs), stats.done, len(stats.failed)))
    if stats.failed:
        os.makedirs(FAILED_DIR, exist_ok=True)
        with open(os.path.join(FAILED_DIR, "lucide_backfill.json"), "w", encoding="utf-8") as fh:
            json.dump(stats.failed, fh, ensure_ascii=False, indent=1)
    manifest["failed"] = [e for e in manifest.get("failed", [])
                          if not os.path.exists(os.path.join(
                              luc_dir, e.split(":", 1)[0].strip() + ".svg"))]
    manifest["count"] = sum(1 for fn in os.listdir(luc_dir) if fn.endswith(".svg"))
    manifest["backfilledAt"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["backfillSource"] = "npm:lucide-static@%s via jsDelivr" % version
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    log("[lucide] backfill complete: done=%d failed=%d total svg now=%d (remaining failed: %d)"
        % (stats.done, len(stats.failed), manifest["count"], len(manifest["failed"])))
    # stale meta (count changed) -> drop it; `meta` command will rebuild
    meta_path = os.path.join(luc_dir, "_meta.json")
    if os.path.exists(meta_path):
        os.remove(meta_path)


def cmd_verify():
    log("=== VERIFY: integrity check across all libraries ===")
    root_libs = sorted(d for d in os.listdir(ICONS_ROOT)
                       if os.path.isdir(os.path.join(ICONS_ROOT, d)) and d != "_collector")
    ok = True
    for lib in root_libs:
        lib_dir = os.path.join(ICONS_ROOT, lib)
        svgs = []
        parts = []
        for root, _dirs, files in os.walk(lib_dir):
            for fn in files:
                p = os.path.join(root, fn)
                if fn.endswith(".part"):
                    parts.append(p)
                elif fn.endswith(".svg"):
                    svgs.append(p)
        bad = []
        for p in (svgs[::max(1, len(svgs) // 20)][:20] if svgs else []):
            try:
                with open(p, "rb") as fh:
                    head = fh.read(4096)
                if b"<svg" not in head or b"<html" in head:
                    bad.append(os.path.basename(p))
            except Exception as e:
                bad.append("%s (%s)" % (os.path.basename(p), e))
        meta_path = os.path.join(lib_dir, "_meta.json")
        meta_total = None
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta_total = json.load(fh).get("total")
        match = (meta_total is None) or (meta_total == len(svgs))
        status = "OK" if (not parts and not bad and match) else "CHECK"
        if status != "OK":
            ok = False
        log("VERIFY [%s] svgs=%d meta=%s parts=%d badSamples=%s -> %s"
            % (lib, len(svgs), meta_total, len(parts), bad or "none", status))
    log("VERIFY RESULT: %s" % ("ALL OK" if ok else "ISSUES FOUND"))


def main():
    global LOG_FH
    os.makedirs(COLLECTOR_DIR, exist_ok=True)
    LOG_FH = open(LOG_PATH, "a", encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = None
    if len(sys.argv) > 3 and sys.argv[2] == "--only":
        only = set(x.strip() for x in sys.argv[3].split(",") if x.strip())
    if cmd == "discover":
        cmd_discover()
    elif cmd == "download":
        cmd_download(only)
    elif cmd == "meta":
        cmd_meta()
    elif cmd == "verify":
        cmd_verify()
    elif cmd == "fix-lucide":
        cmd_fix_lucide()
    elif cmd == "all":
        cmd_discover()
        cmd_download()
    else:
        log("unknown command: %s (use discover|download|meta|verify|all)" % cmd)
    if LOG_FH:
        LOG_FH.close()


if __name__ == "__main__":
    main()
