"""SiYuan Kernel API helper — the reference implementation for siyuan-kernel-ops.

Usage from an agent session (replace <skill dir> with the skill's base directory):

    import sys; sys.path.insert(0, r"<skill dir>/scripts")
    from sy import connect, call
    base, token = connect()
    call(base, token, "/api/notebook/lsNotebooks")

Connection lookup: SIYUAN_URL + SIYUAN_TOKEN, then every conf.json found among
SIYUAN_CONF / the default workspace / %USERPROFILE%\\SiYuan\\conf / sibling
workspaces under the same data root. Each token is validated against
/api/notebook/lsNotebooks, so stale configs are skipped instead of trusted.

Smoke test: python sy.py
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CONF = Path(r"D:\MyData\Warehouse\siyuan-backup\conf\conf.json")


def _urls(conf, env_url=""):
    urls = []
    if env_url:
        urls.append(env_url.rstrip("/"))
    for value in conf.get("serverAddrs") or []:
        if isinstance(value, str) and value.startswith(("http://127.0.0.1:", "http://localhost:")):
            urls.append(value.rstrip("/"))
    urls.append("http://127.0.0.1:6806")
    return list(dict.fromkeys(urls))


def candidate_conf_files():
    """Workspace configs to try, in priority order. Missing files are ignored."""
    paths = []
    env = os.environ.get("SIYUAN_CONF")
    if env:
        paths.append(Path(env))
    paths.append(DEFAULT_CONF)
    paths.append(Path.home() / "SiYuan" / "conf" / "conf.json")
    try:
        data_root = DEFAULT_CONF.parents[3]
    except IndexError:
        data_root = None
    if data_root and data_root.is_dir():
        paths.extend(sorted(data_root.glob("*/conf/conf.json")))
    seen, result = set(), []
    for path in paths:
        key = os.path.normcase(str(path))
        if key not in seen and path.is_file():
            seen.add(key)
            result.append(path)
    return result


def load_connections():
    """Return [(label, token, urls)] candidates, deduplicated by (token, urls)."""
    env_url = os.environ.get("SIYUAN_URL", "").rstrip("/")
    env_token = os.environ.get("SIYUAN_TOKEN", "").strip()
    candidates, searched = [], [str(DEFAULT_CONF)]
    if env_token:
        candidates.append(("env SIYUAN_TOKEN", env_token, _urls({}, env_url)))
    for path in candidate_conf_files():
        searched.append(str(path))
        conf = json.loads(path.read_text(encoding="utf-8-sig"))
        token = ((conf.get("api") or {}).get("token") or "").strip()
        if token:
            candidates.append((str(path), token, _urls(conf, env_url)))
    if not candidates:
        raise RuntimeError("SiYuan API token not found; searched " + ", ".join(dict.fromkeys(searched)))
    seen, result = set(), []
    for label, token, urls in candidates:
        key = (token, tuple(urls))
        if key not in seen:
            seen.add(key)
            result.append((label, token, urls))
    return result


def load_connection():
    """Backward-compatible: (urls, token) of the first candidate."""
    _label, token, urls = load_connections()[0]
    return urls, token


def call(base, token, path, payload=None, timeout=30):
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"SiYuan request failed at {path}: {type(exc).__name__}") from exc
    if not isinstance(result, dict) or result.get("code") != 0:
        msg = result.get("msg", "malformed response") if isinstance(result, dict) else "malformed response"
        raise RuntimeError(f"SiYuan API error at {path}: {msg}")
    return result.get("data")


def connect():
    errors = []
    for label, token, urls in load_connections():
        for base in urls:
            try:
                data = call(base, token, "/api/notebook/lsNotebooks", {}, 5)
                if isinstance(data, dict) and isinstance(data.get("notebooks"), list):
                    return base, token
            except Exception as exc:
                errors.append(f"{base} [{label}]: {type(exc).__name__}")
    raise RuntimeError("No authenticated SiYuan kernel found; " + "; ".join(errors))


if __name__ == "__main__":
    base, token = connect()
    notebooks = call(base, token, "/api/notebook/lsNotebooks")["notebooks"]
    version = call(base, token, "/api/system/version")
    print(f"kernel : {base}")
    print(f"version: {version}")
    print(f"notebooks: {len(notebooks)}")
    for nb in notebooks:
        state = "closed" if nb.get("closed") else "open"
        print(f"  {nb['id']}  {nb['name']}  ({state})")
