"""
Git Local Tool - minimal Git operations via local CLI
- merge: fast-forward (par défaut) ou merge-commit, puis push optionnel
- list_branches, current_branch, status, pull, push
- clone: cloner un dépôt dans <racine_projet>/clone/<nom>

Prérequis: git installé. Les chemins peuvent être relatifs à la racine du projet (dossier qui contient 'src').
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _project_root() -> Path:
    cur = Path.cwd()
    while cur != cur.parent:
        if (cur / "src").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def _resolve_path(p: Optional[str]) -> Path:
    if not p:
        return _project_root()
    q = Path(p).expanduser()
    return q if q.is_absolute() else (_project_root() / q).resolve()


def _run(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        return {
            "cmd": " ".join(cmd),
            "returncode": p.returncode,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "success": p.returncode == 0,
        }
    except FileNotFoundError:
        return {"success": False, "error": "git not found in PATH"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _ensure_repo(path: Path) -> None:
    if not path.exists() or not (path / ".git").exists():
        raise ValueError(f"Not a git repo: {path}")


def run(operation: str, **params) -> Dict[str, Any]:
    op = (operation or "").strip().lower()

    # --- clone (ne nécessite pas repo_dir) ---
    if op == "clone":
        repo_url = params.get("repo_url")
        name = params.get("name")  # nom du dossier cible
        dest_dir = _resolve_path(params.get("dest_dir") or "clone")
        if not repo_url:
            return {"error": "repo_url is required for clone"}
        # déterminer le nom
        if not name:
            if repo_url.endswith(".git"):
                name = Path(repo_url).stem
            else:
                name = repo_url.rstrip("/").split("/")[-1]
        target = dest_dir / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # nettoyage (simple) via git
            # si échec, l'utilisateur supprimera manuellement
            pass
        step = _run(["git", "clone", repo_url, str(target)], _project_root())
        return {"success": step.get("success", False), "target": str(target), "dest_dir": str(dest_dir), "step": step}

    # --- autres opérations nécessitent repo_dir ---
    repo_dir_param = params.get("repo_dir") or params.get("path") or params.get("repo_path")
    if op not in {"list_branches", "current_branch", "status", "pull", "push", "merge"}:
        return {"error": f"Unknown operation: {operation}"}
    if not repo_dir_param:
        return {"error": "repo_dir is required (path to local clone)"}

    try:
        repo = _resolve_path(repo_dir_param)
        _ensure_repo(repo)
    except Exception as e:
        return {"error": str(e)}

    steps: List[Dict[str, Any]] = []

    if op == "list_branches":
        steps.append(_run(["git", "fetch", "--all", "--prune"], repo))
        steps.append(_run(["git", "branch", "-a", "--format=%(refname:short)"], repo))
        out = steps[-1].get("stdout", "")
        branches = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return {"success": True, "repo": str(repo), "branches": branches, "steps": steps}

    if op == "current_branch":
        steps.append(_run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo))
        cb = steps[-1].get("stdout", "")
        return {"success": steps[-1].get("success", False), "repo": str(repo), "current_branch": cb, "steps": steps}

    if op == "status":
        steps.append(_run(["git", "status", "--porcelain=v1"], repo))
        steps.append(_run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo))
        steps.append(_run(["git", "log", "-1", "--format=%H %cI %s"], repo))
        return {
            "success": all(s.get("success", False) for s in steps),
            "repo": str(repo),
            "porcelain": steps[0].get("stdout", ""),
            "branch": steps[1].get("stdout", ""),
            "last_commit": steps[2].get("stdout", ""),
            "steps": steps,
        }

    if op == "pull":
        remote = params.get("remote", "origin")
        branch = params.get("branch")
        if not branch:
            cur = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
            steps.append(cur)
            branch = cur.get("stdout", "")
        steps.append(_run(["git", "fetch", "--all", "--prune"], repo))
        steps.append(_run(["git", "pull", remote, branch], repo))
        ok = all(s.get("success", False) for s in steps)
        return {"success": ok, "repo": str(repo), "branch": branch, "steps": steps}

    if op == "push":
        remote = params.get("remote", "origin")
        branch = params.get("branch")
        if not branch:
            cur = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
            steps.append(cur)
            branch = cur.get("stdout", "")
        steps.append(_run(["git", "push", remote, branch], repo))
        ok = all(s.get("success", False) for s in steps)
        return {"success": ok, "repo": str(repo), "branch": branch, "steps": steps}

    if op == "merge":
        base = params.get("base", "main")
        head = params.get("head")
        if not head:
            return {"error": "head (source branch) is required"}
        remote = params.get("remote", "origin")
        ff_only = bool(params.get("ff_only", True))
        push_after = bool(params.get("push", True))
        message = params.get("message") or f"merge {head} into {base}"

        steps.append(_run(["git", "fetch", "--all", "--prune"], repo))
        steps.append(_run(["git", "checkout", base], repo))
        steps.append(_run(["git", "pull", remote, base], repo))
        steps.append(_run(["git", "fetch", remote, head], repo))

        if ff_only:
            steps.append(_run(["git", "merge", "--ff-only", f"{remote}/{head}"], repo))
        else:
            steps.append(_run(["git", "merge", "--no-ff", f"{remote}/{head}", "-m", message], repo))

        ok_merge = steps[-1].get("success", False)
        if not ok_merge:
            return {"success": False, "repo": str(repo), "base": base, "head": head, "steps": steps}

        if push_after:
            steps.append(_run(["git", "push", remote, base], repo))

        ok = all(s.get("success", False) for s in steps)
        return {"success": ok, "repo": str(repo), "base": base, "head": head, "steps": steps}

    return {"error": f"Unhandled operation: {operation}"}


def spec() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "git_local",
            "description": "Git local via CLI: clone, list_branches, current_branch, status, pull, push, merge (ff-only par défaut). Les chemins peuvent être relatifs à la racine du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["clone", "list_branches", "current_branch", "status", "pull", "push", "merge"],
                        "description": "Type d'opération Git locale"
                    },
                    "repo_dir": {"type": "string", "description": "Chemin du repo local (pour toutes les opérations sauf clone). Relatif possible (ex: 'clone/mcp-server-tools')."},
                    "repo_url": {"type": "string", "description": "URL du dépôt à cloner (clone)"},
                    "dest_dir": {"type": "string", "description": "Dossier destination (relatif/absolu). Défaut: 'clone' à la racine projet (clone)"},
                    "name": {"type": "string", "description": "Nom du dossier de clone (déduit de l'URL si absent)"},
                    "remote": {"type": "string", "description": "Nom du remote (défaut: origin)"},
                    "branch": {"type": "string", "description": "Branche cible pour pull/push (détection auto si absent)"},
                    "base": {"type": "string", "description": "Branche de base pour merge (défaut: main)"},
                    "head": {"type": "string", "description": "Branche source à fusionner (ex: feat/xyz)"},
                    "ff_only": {"type": "boolean", "description": "Forcer fast-forward only (défaut: true)"},
                    "push": {"type": "boolean", "description": "Pousser après merge (défaut: true)"},
                    "message": {"type": "string", "description": "Message de merge si --no-ff"}
                },
                "required": ["operation"],
                "additionalProperties": False
            }
        }
    }
