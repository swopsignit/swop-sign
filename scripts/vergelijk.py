#!/usr/bin/env python3
"""Vergelijkt een release-zip uit Swop Hub bestand voor bestand met de bron op een commit.

Gebruik: vergelijk.py <zip> <bronmap> <kind> <slug> <versie> [vorig-manifest.json]
  <bronmap> = de map in de uitgepakte repo die de pluginmap vormt, bijv. .../bron/swop-canvas-bridge
Schrijft een JSON-uitslag naar stdout. Exitcode 0 = gelijk, 1 = afgekeurd (reden in "fouten").

Regels:
- Alles in de zip staat onder <slug>/; geen absolute paden, geen "..", geen symlinks.
- Elk bestand in de zip bestaat in de bron en is byte voor byte gelijk.
- Bestanden in de bron die niet in de zip staan zijn alleen toegestaan als ontwikkelbestand (tests/, docs/,
  LEESMIJ.md enz.); andere ontbrekende bestanden worden gemeld maar keuren niet af.
- De versie in het hoofdbestand (plugin: <slug>/<slug>.php, thema: <slug>/style.css) is gelijk aan <versie>.
Alleen de standaardbibliotheek, zodat er niets geïnstalleerd hoeft te worden.
"""
import hashlib, json, os, re, stat, sys, zipfile

DEV_DIRS = ("tests/", "test/", "node_modules/", ".git/", ".github/", "docs/")
DEV_FILES = {".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes", "LEESMIJ.md"}


def is_dev(rel):
    base = rel.rsplit("/", 1)[-1]
    return base in DEV_FILES or any(rel.startswith(d) or ("/" + d) in rel for d in DEV_DIRS)


def header_version(text, kind):
    pat = r"^[ \t/*#@]*Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$"
    m = re.search(pat, text, re.M | re.I)
    return m.group(1) if m else None


def main():
    if len(sys.argv) < 6:
        print(json.dumps({"ok": False, "fouten": ["Te weinig argumenten."]}))
        return 1
    zip_path, src_root, kind, slug, version = sys.argv[1:6]
    previous = {}
    if len(sys.argv) > 6 and os.path.isfile(sys.argv[6]):
        try:
            previous = json.load(open(sys.argv[6])).get("bestanden", {})
        except Exception:
            previous = {}
    errors, warnings, files = [], [], {}
    if kind not in ("plugin", "theme", "bridge"):
        errors.append(f"Onbekende soort {kind}.")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errors.append("Ongeldige slug.")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("Versie moet x.y.z zijn.")
    if not os.path.isdir(src_root):
        errors.append("Bronmap bestaat niet op deze commit.")
    if errors:
        print(json.dumps({"ok": False, "fouten": errors}, ensure_ascii=False))
        return 1

    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            if name.startswith("/") or "\\" in name or ".." in name.split("/"):
                errors.append(f"Ongeldig pad in de zip: {name}")
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                errors.append(f"Symlink in de zip: {name}")
                continue
            if not name.startswith(slug + "/"):
                errors.append(f"Bestand buiten de map {slug}/: {name}")
                continue
            rel = name[len(slug) + 1:]
            data = z.read(info)
            src = os.path.join(src_root, rel)
            if not os.path.isfile(src) or os.path.islink(src):
                errors.append(f"Staat niet in de bron op deze commit: {rel}")
                continue
            if open(src, "rb").read() != data:
                errors.append(f"Wijkt af van de bron: {rel}")
                continue
            files[rel] = hashlib.sha256(data).hexdigest()

    for root, dirs, names in os.walk(src_root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), src_root).replace(os.sep, "/")
            if rel not in files and not is_dev(rel) and not any(e.endswith(": " + rel) for e in errors):
                warnings.append(f"Staat in de bron maar niet in de zip: {rel}")

    main_file = {"plugin": f"{slug}.php", "bridge": f"{slug}.php", "theme": "style.css"}[kind]
    if main_file not in files:
        if not any(e.endswith(": " + main_file) for e in errors):
            errors.append(f"Hoofdbestand {slug}/{main_file} ontbreekt.")
    else:
        found = header_version(open(os.path.join(src_root, main_file), encoding="utf-8", errors="replace").read(), kind)
        if found != version:
            errors.append(f"Versie in {main_file} is {found}, niet {version}.")

    changed = sorted(r for r in files if previous.get(r) != files[r])
    removed = sorted(r for r in previous if r not in files)
    result = {
        "ok": not errors,
        "fouten": errors,
        "waarschuwingen": warnings[:50],
        "aantal_bestanden": len(files),
        "gewijzigd_sinds_vorige": changed if previous else None,
        "verwijderd_sinds_vorige": removed if previous else None,
        "bestanden": files,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
