#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_env.py -- is there a usable LaTeX toolchain on this machine, and what is missing?

Read-only by default. The only mode that touches the network or installs anything is --install.

  python check_env.py                                  # report only
  python check_env.py --need subfig.sty,algorithmic.sty,FandolSong-Regular.otf
     # 宏包写 xxx.sty，字体写具体字体文件名——字体类包没有 .sty，按包名查会误报缺失
  python check_env.py --install --extra subfig,dblfloatfix,algorithmic

Exit code 0 = a pdflatex was found and every --need package resolves; 1 otherwise. That makes it
usable as a gate in a build script.

Why the install path matters: on a machine where elevation is blocked, a TeX distribution has to go
in per-user / portable, and on a machine whose system drive gets wiped it should not live on C:.
The recipe here does both -- TeX Live, scheme-small, into --texdir, no admin, no PATH changes.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ENGINES = ["pdflatex", "xelatex", "lualatex", "latexmk", "bibtex", "biber", "kpsewhich", "tlmgr"]
DEFAULT_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet"


def default_texdir():
    """Prefer a non-system drive: the system drive on these machines tends to get reset."""
    for drive in ("D:/", "E:/"):
        if os.path.isdir(drive):
            return drive + "Software/texlive"
    return "C:/texlive"


def candidate_bindirs(texdir):
    """Every place we would believe a TeX installation lives."""
    out = []
    roots = [texdir, "D:/Software/texlive", "C:/texlive"]
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if appdata:
        roots.append(os.path.join(appdata, "TinyTeX"))
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        for name in sorted(os.listdir(r)):
            for sub in ("bin/windows", "bin/x86_64-windows", "bin"):
                d = os.path.join(r, name, sub).replace("\\", "/")
                if os.path.isdir(d):
                    out.append(d)
        # TinyTeX style: <root>/bin/windows
        d = os.path.join(r, "bin", "windows").replace("\\", "/")
        if os.path.isdir(d):
            out.append(d)
    for extra in ("C:/Program Files/MiKTeX/miktex/bin/x64",
                  localappdata + "/Programs/MiKTeX/miktex/bin/x64"):
        if extra and os.path.isdir(extra):
            out.append(extra)
    return out


def find_tools(texdir):
    """Return {tool: full path} for whatever we can locate."""
    found = {}
    for tool in ENGINES:
        w = shutil.which(tool)
        if w:
            found[tool] = w
    for d in candidate_bindirs(texdir):
        for tool in ENGINES:
            if tool in found:
                continue
            # Windows: most TeX binaries are .exe, but tlmgr is a .bat wrapper.
            for ext in (".exe", ".bat", ""):
                exe = os.path.join(d, tool + ext)
                if os.path.isfile(exe):
                    found[tool] = exe.replace("\\", "/")
                    break
    return found


def version_of(path):
    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True,
                           errors="replace", timeout=30)
        line = (r.stdout or r.stderr).strip().splitlines()
        if line:
            return line[0][:60]
        return "(无输出, rc=%d)" % r.returncode
    except Exception as e:  # noqa: BLE001
        return "调用失败: %s" % type(e).__name__


def check_packages(kpsewhich, names):
    missing = []
    for n in names:
        if not n:
            continue
        hit = None
        for ext in (".sty", ".cls", ".def", ""):
            r = subprocess.run([kpsewhich, n + ext], capture_output=True, text=True,
                           errors="replace", timeout=60)
            if r.stdout.strip():
                hit = r.stdout.strip()
                break
        print("    %-20s %s" % (n, hit if hit else "**缺失**"))
        if not hit:
            missing.append(n)
    return missing


def do_install(texdir, setup_dir, mirror, scheme, extra, year):
    """Portable, per-user, no PATH changes. Returns the bin dir or None."""
    os.makedirs(setup_dir, exist_ok=True)
    zip_path = os.path.join(setup_dir, "install-tl.zip")
    url = mirror.rstrip("/") + "/install-tl.zip"
    print("[1/4] 下载安装器 %s（约 24 MB）" % url)
    urllib.request.urlretrieve(url, zip_path)
    print("[2/4] 解压到 %s" % setup_dir)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(setup_dir)
    root = None
    for name in os.listdir(setup_dir):
        if name.startswith("install-tl-"):
            root = os.path.join(setup_dir, name)
    if not root:
        print("     未找到解压后的安装器目录"); return None
    profile = os.path.join(setup_dir, "texlive.profile")
    texdir_fwd = texdir.replace("\\", "/").rstrip("/")
    with open(profile, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([
            "selected_scheme scheme-%s" % scheme,
            "TEXDIR %s/%s" % (texdir_fwd, year),
            "TEXMFLOCAL %s/texmf-local" % texdir_fwd,
            "TEXMFSYSCONFIG %s/%s/texmf-config" % (texdir_fwd, year),
            "TEXMFSYSVAR %s/%s/texmf-var" % (texdir_fwd, year),
            "TEXMFCONFIG ~/.texlive%s/texmf-config" % year,
            "TEXMFVAR ~/.texlive%s/texmf-var" % year,
            "TEXMFHOME ~/texmf",
            "instopt_adjustpath 0",      # we call the binaries by absolute path
            "instopt_adjustrepo 0",
            "instopt_letter 0",
            "instopt_portable 0",
            "instopt_write18_restricted 1",
            "tlpdbopt_autobackup 0",
            "tlpdbopt_install_docfiles 0",   # docs and sources are most of the bytes
            "tlpdbopt_install_srcfiles 0",
        ]) + "\n")
    bat = os.path.join(root, "install-tl-windows.bat")
    print("[3/4] 安装到 %s（scheme-%s，免管理员）..." % (texdir, scheme))
    log = os.path.join(setup_dir, "install.log")
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        rc = subprocess.run(["cmd", "/c", bat, "-no-gui", "-profile", profile, "-repo", mirror],
                            cwd=root, stdout=fh, stderr=subprocess.STDOUT).returncode
    print("     退出码 %d，日志 %s" % (rc, log))
    if rc != 0:
        print("     安装未成功；日志尾部：")
        with open(log, encoding="utf-8", errors="replace") as fh:
            print("".join(fh.readlines()[-12:]))
        return None
    bindir = "%s/%s/bin/windows" % (texdir_fwd, year)
    if extra:
        tlmgr = None
        for name in ("tlmgr.bat", "tlmgr.exe", "tlmgr"):
            cand = os.path.join(bindir.replace("/", os.sep), name)
            if os.path.isfile(cand):
                tlmgr = cand
                break
        if tlmgr:
            print("[4/4] 补装宏包: %s" % extra)
            subprocess.run([tlmgr, "install"] + extra.split(","), timeout=1800)
        else:
            print("[4/4] 未找到 tlmgr，跳过补装")
    return bindir


def main():
    ap = argparse.ArgumentParser(description="检查（或安装）本机 LaTeX 环境")
    ap.add_argument("--texdir", default=default_texdir(), help="安装根目录，默认避开系统盘")
    ap.add_argument("--need", default="", help="要核实的宏包/类名，逗号分隔")
    ap.add_argument("--install", action="store_true", help="缺失时安装 TeX Live（portable，免管理员）")
    ap.add_argument("--scheme", default="small", help="安装 scheme（small/medium/full）")
    ap.add_argument("--extra", default="", help="装完用 tlmgr 追加的宏包，逗号分隔")
    ap.add_argument("--mirror", default=DEFAULT_MIRROR)
    ap.add_argument("--year", default="2026")
    args = ap.parse_args()

    print("=== LaTeX 环境检查 ===")
    tools = find_tools(args.texdir)
    for t in ENGINES:
        print("  %-12s %s" % (t, (tools[t] + "   " + version_of(tools[t])) if t in tools else "**未找到**"))

    missing = []
    if args.need and "kpsewhich" in tools:
        print("\n=== 宏包核实（kpsewhich）===")
        missing = check_packages(tools["kpsewhich"], args.need.split(","))
    elif args.need:
        missing = args.need.split(",")
        print("\n=== 宏包核实 ===\n    无 kpsewhich，无法核实")

    need_install = ("pdflatex" not in tools) or bool(missing)
    if args.install and need_install:
        print("\n=== 执行安装 ===")
        bindir = do_install(args.texdir, os.path.join(args.texdir, "_setup"),
                            args.mirror, args.scheme, args.extra, args.year)
        if bindir:
            tools = find_tools(args.texdir)
            if args.need and "kpsewhich" in tools:
                print("\n=== 复检宏包 ===")
                missing = check_packages(tools["kpsewhich"], args.need.split(","))

    if "pdflatex" in tools:
        bindir = os.path.dirname(tools["pdflatex"]).replace("\\", "/")
        print("\n=== 编译时怎么用 ===")
        print("  bin 目录: %s" % bindir)
        print("  绝对路径调用（不依赖 PATH）: %s" % tools["pdflatex"])
        print("  临时加入 PATH:  export PATH=\"%s:$PATH\"" % bindir)
        print("  编译两遍即可定页码:  pdflatex -interaction=nonstopmode -halt-on-error main.tex")

    ok = ("pdflatex" in tools) and not missing
    print("\n结论: %s%s" % ("可用" if ok else "不可用",
                          ("；缺 %s" % ",".join(missing)) if missing else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
