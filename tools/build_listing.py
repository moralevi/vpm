"""Build the VCC/VPM listing (index.json) from this repo's GitHub releases.

Every published release that has a `package.json` asset and the zip named in its "url" becomes one
package version in the listing. Output goes to the folder given as the first argument (default: _site).

Env: GITHUB_REPOSITORY (owner/name), GITHUB_TOKEN (optional, raises the API rate limit).
"""
import hashlib, html, json, os, sys, urllib.request

LISTING = {
    "name": "moralevi VPM",
    "id": "com.nyanfound.vpm",
    "url": "https://moralevi.github.io/vpm/index.json",
    "author": "Mora",
}

REPO = os.environ.get("GITHUB_REPOSITORY", "moralevi/vpm")
TOKEN = os.environ.get("GITHUB_TOKEN")


def get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "vpm-listing-builder"})
    if TOKEN and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req) as r:
        return r.read()


def releases():
    page = 1
    while True:
        batch = json.loads(get(f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}"))
        if not batch:
            return
        yield from batch
        page += 1


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "_site"
    os.makedirs(out, exist_ok=True)
    packages = {}
    rows = []
    for rel in releases():
        if rel.get("draft"):
            continue
        assets = {a["name"]: a for a in rel.get("assets", [])}
        if "package.json" not in assets:
            print(f"skip {rel['tag_name']}: no package.json asset")
            continue
        pkg = json.loads(get(assets["package.json"]["browser_download_url"], "application/octet-stream"))
        zip_name = pkg["url"].rsplit("/", 1)[-1].split("?")[0]
        if zip_name not in assets:
            print(f"skip {rel['tag_name']}: zip {zip_name} not attached")
            continue
        pkg["zipSHA256"] = hashlib.sha256(get(assets[zip_name]["browser_download_url"], "application/octet-stream")).hexdigest()
        packages.setdefault(pkg["name"], {"versions": {}})["versions"][pkg["version"]] = pkg
        rows.append((pkg.get("displayName", pkg["name"]), pkg["version"], rel["html_url"]))
        print(f"added {pkg['name']} {pkg['version']}")

    listing = dict(LISTING, packages=packages)
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(listing, f, indent=2)
        f.write("\n")

    items = "\n".join(f'<li><a href="{html.escape(u)}">{html.escape(n)} {html.escape(v)}</a></li>' for n, v, u in rows)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><meta charset="utf-8"><title>moralevi VPM</title>
<style>body{{font-family:system-ui,sans-serif;background:#16121f;color:#ece4ff;max-width:640px;margin:40px auto;padding:0 16px}}
a{{color:#c9a2ff}}code{{background:#2b2338;padding:2px 6px;border-radius:4px}}</style>
<h1>moralevi VPM</h1>
<p>VRChat packages by Mora. NekoToon is made for 404NyanFound.</p>
<p>Add this repository in VCC or ALCOM (Settings &rarr; Packages &rarr; Add Repository):</p>
<p><code>{html.escape(LISTING['url'])}</code></p>
<h2>Packages</h2><ul>{items}</ul>
""")


if __name__ == "__main__":
    main()
