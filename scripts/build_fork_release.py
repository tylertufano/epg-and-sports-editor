#!/usr/bin/env python3
"""Build a fork release of EPG & Sports Editor and its Dispatcharr repository manifests.

Usage: python scripts/build_fork_release.py VERSION
  e.g. python scripts/build_fork_release.py 0.6.03.2

Sets the version in BOTH places Dispatcharr reads (plugin.py's Plugin.version wins over
plugin.json's), builds dist/epg-and-sports-editor-vVERSION.zip (plugin.json, plugin.py,
logo.png), and rewrites manifest.json and zips/epg-and-sports-editor/manifest.json for the
tufanito-release branch (keeping earlier versions' entries). Then: commit, push, and
`gh release create vVERSION dist/...zip --target tufanito-release`.
Fork versions are upstream's + a 4th number (0.6.03.N): above upstream 0.6.03, below 0.6.04.
"""
import datetime, hashlib, json, re, sys, zipfile
from pathlib import Path

OWNER, REPO, BRANCH = "tylertufano", "epg-and-sports-editor", "tufanito-release"
ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+(\.\d+){3}", sys.argv[1]):
        sys.exit("usage: build_fork_release.py VERSION (four numeric parts, e.g. 0.6.03.2)")
    v = sys.argv[1]
    py = ROOT / "plugin.py"
    src, n = re.subn(r'(?m)^(\s*version\s*=\s*)"[^"]*"', rf'\g<1>"{v}"', py.read_text(encoding="utf-8"), count=1)
    if n != 1:
        sys.exit("plugin.py: no class version line found")
    py.write_text(src, encoding="utf-8")
    pj_path = ROOT / "plugin.json"
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    pj["version"] = v
    pj_path.write_text(json.dumps(pj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    dist = ROOT / "dist"; dist.mkdir(exist_ok=True)
    zp = dist / f"{REPO}-v{v}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ("plugin.json", "plugin.py", "logo.png"):
            z.write(ROOT / f, f)
    data = zp.read_bytes()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://github.com/{OWNER}/{REPO}/releases/download/v{v}/{zp.name}"
    entry = {"version": v, "url": url, "checksum_md5": hashlib.md5(data).hexdigest(),
             "checksum_sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
             "last_updated": now, "build_timestamp": now, "min_dispatcharr_version": "0.34.0"}
    desc = pj["description"].split("\n\n")[0]
    pm_path = ROOT / "zips" / REPO / "manifest.json"
    old = json.loads(pm_path.read_text(encoding="utf-8")).get("manifest", {}) if pm_path.exists() else {}
    earlier = [e for e in old.get("versions", []) if e.get("version") != v and "/tylertufano/" in e.get("url", "")]
    pm = {"generated_at": now, "manifest": {
        "slug": REPO, "name": pj["name"], "description": desc, "author": "jstevenscl (fork: tylertufano)",
        "registry_url": f"https://github.com/{OWNER}/{REPO}", "registry_name": f"{OWNER}/{REPO}", "last_updated": now,
        "latest": {**entry, "latest_url": url}, "versions": [entry] + earlier}}
    pm_path.write_text(json.dumps(pm, indent=2) + "\n", encoding="utf-8")
    root = {"generated_at": now, "manifest": {
        "registry_url": f"https://github.com/{OWNER}/{REPO}", "registry_name": f"{OWNER}/{REPO} (fork)",
        "root_url": f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}",
        "plugins": [{"slug": REPO, "name": pj["name"], "description": desc, "manifest_url": f"zips/{REPO}/manifest.json",
                     "author": "jstevenscl (fork: tylertufano)", "license": "MIT", "last_updated": now,
                     "latest_version": v, "latest_md5": entry["checksum_md5"], "latest_sha256": entry["checksum_sha256"],
                     "latest_url": url, "latest_size": len(data),
                     "help_url": f"https://github.com/{OWNER}/{REPO}/tree/{BRANCH}#documentation",
                     "min_dispatcharr_version": "0.34.0"}]}}
    (ROOT / "manifest.json").write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")
    print(f"{zp.name}: {len(data)} bytes, sha256 {entry['checksum_sha256'][:16]}; manifests updated; {len(earlier)} earlier version(s) kept")


if __name__ == "__main__":
    main()
