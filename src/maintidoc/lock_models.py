"""Fige les révisions exactes des modèles Hugging Face utilisés (config/models.lock.yaml).

Usage : python -m maintidoc.lock_models   (après un premier lancement qui a téléchargé les modèles)
"""

from datetime import date

import yaml
from huggingface_hub import model_info, scan_cache_dir

from maintidoc.config import ROOT, get_settings


def main():
    s = get_settings()
    wanted = {"text_model": s.text_model, "image_model": s.image_model,
              "image_text_model": s.image_text_model, "reranker_model": s.reranker_model}
    cached = {r.repo_id: r for r in scan_cache_dir().repos}
    out = {"generated": date.today().isoformat(), "models": {}}
    for role, repo in wanted.items():
        entry = {"repo": repo}
        if repo in cached:
            revs = sorted(cached[repo].revisions, key=lambda r: r.last_modified, reverse=True)
            entry["revision"] = revs[0].commit_hash
            entry["size_mb"] = round(cached[repo].size_on_disk / 1e6)
        try:
            info = model_info(repo)
            entry["license"] = next((t.split(":", 1)[1] for t in (info.tags or []) if t.startswith("license:")), None)
        except Exception:
            entry["license"] = "à vérifier (hors ligne)"
        out["models"][role] = entry
    path = ROOT / "config" / "models.lock.yaml"
    path.parent.mkdir(exist_ok=True)
    path.write_text("# Révisions figées des modèles (à utiliser avec revision=... pour reproduire l'index)\n"
                    + yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
