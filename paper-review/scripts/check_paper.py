#!/usr/bin/env python3
"""Static sanity checks for a LaTeX paper before submission.

Read-only: this script never writes, moves or deletes anything, never touches the
network, and never spawns a subprocess. It only reads the .tex file (and, when
asked, the .bib file and the figures directory) and prints a report.

Usage:
    python check_paper.py main.tex
    python check_paper.py main.tex --bib references.bib
    python check_paper.py main.tex --figdir figures

Every check is best-effort static analysis. A FAIL means a rule is definitely
broken; a WARN is something a human must look at, because the correct form
depends on pronunciation, on which term was introduced where, or on facts the
script cannot see.

Exit code: 0 when there is no FAIL, 1 otherwise. Warnings do not fail the run.
"""

import argparse
import os
import re
import sys

# --- findings -------------------------------------------------------------

FAILS = []
WARNS = []
PASSES = []


def fail(tag, msg):
    FAILS.append((tag, msg))


def warn(tag, msg):
    WARNS.append((tag, msg))


def ok(tag, msg=""):
    PASSES.append((tag, msg))


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


# --- individual checks ----------------------------------------------------

def check_ascii(src):
    bad = [(lineno(src, i), c) for i, c in enumerate(src) if ord(c) > 127]
    if bad:
        where = ", ".join("L%d U+%04X" % (l, ord(c)) for l, c in bad[:12])
        more = "" if len(bad) <= 12 else " (+%d more)" % (len(bad) - 12)
        fail("ascii", "non-ASCII characters in source: %s%s" % (where, more))
    else:
        ok("ascii", "pure ASCII")


def check_braces(src):
    d = src.count("{") - src.count("}")
    if d:
        fail("braces", "unbalanced braces, difference %+d" % d)
    else:
        ok("braces", "balanced")


def check_dollars(src):
    n = src.count("$") - 2 * src.count("$$")
    if n % 2:
        fail("math", "odd number of $ delimiters (%d)" % n)
    else:
        ok("math", "$ count even (%d)" % n)


def check_environments(src, names):
    for env in names:
        begins = len(re.findall(r"\\begin\{%s\}" % re.escape(env), src))
        ends = len(re.findall(r"\\end\{%s\}" % re.escape(env), src))
        if begins != ends:
            fail("env:" + env, "\\begin{%s}=%d but \\end{%s}=%d" % (env, begins, env, ends))
        elif begins:
            ok("env:" + env, "%d pair(s)" % begins)


def check_graphics(src, base, figdir):
    missing = []
    for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", src):
        rel = m.group(1)
        cands = [os.path.join(base, rel)]
        if figdir:
            cands.append(os.path.join(base, figdir, os.path.basename(rel)))
            cands.append(os.path.join(base, os.path.basename(rel)))
        if not any(os.path.exists(c) for c in cands):
            missing.append((lineno(src, m.start()), rel))
    if missing:
        for l, rel in missing:
            fail("graphics", "L%d file not found: %s" % (l, rel))
    else:
        ok("graphics", "all \\includegraphics files exist")


def check_text_math(src):
    """\\text{} is text mode; math-only commands inside it break the build."""
    MATH_ONLY = ("mu", "cdot", "times", "circ", "Delta", "pm", "approx",
                 "alpha", "beta", "gamma", "sigma", "lambda", "Omega",
                 "le", "ge", "neq", "rightarrow")
    hits = []
    for m in re.finditer(r"\\text\{([^{}]*)\}", src):
        inner = m.group(1)
        for cmd in MATH_ONLY:
            if "\\" + cmd in inner:
                hits.append((lineno(src, m.start()), cmd, inner))
    if hits:
        for l, cmd, inner in hits:
            fail("text-math", "L%d math-only \\%s inside \\text{%s}" % (l, cmd, inner))
    else:
        ok("text-math", "no math-only commands inside \\text{}")


def check_bib_entries_quality(bibtxt):
    """Audit .bib entries for IEEEtran.bst silent formatting traps."""
    entries = re.split(r"(?=@\w+\s*\{)", bibtxt)
    issues = 0
    for ent in entries:
        m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", ent)
        if not m:
            continue
        etype, key = m.group(1).lower(), m.group(2)
        if re.search(r"\band\s+others\b", ent, re.I):
            warn("bib-style", "%s: 'and others' hardcoded in author; list all authors "
                              "so IEEEtran.bst truncates >=7 automatically" % key)
            issues += 1
        mp = re.search(r"\bpages\s*=\s*\{([^}]*)\}", ent, re.I)
        if mp:
            pval = mp.group(1).strip()
            if re.match(r"^\d{3,}$", pval):
                warn("bib-style", "%s: single number pages={%s} without '--' will render "
                                  "as 'p. %s'; if it is an article number, use {{Art. no.} %s}"
                     % (key, pval, pval, pval))
                issues += 1
        if etype == "manual":
            ma = re.search(r"\bauthor\s*=\s*\{([^}]*)\}", ent, re.I)
            mo = re.search(r"\borganization\s*=\s*\{([^}]*)\}", ent, re.I)
            if ma and mo and ma.group(1).strip() and ma.group(1).strip() == mo.group(1).strip():
                fail("bib-style", "%s (@manual): identical author and organization '%s' "
                                  "will be printed twice by IEEEtran.bst"
                     % (key, ma.group(1).strip()))
                issues += 1
        mn = re.search(r"\bnote\s*=\s*\{(.*)\}", ent, re.I)
        if mn and "Art. no." in mn.group(1) and "{Art. no.}" not in mn.group(1):
            warn("bib-style", "%s: unprotected 'Art. no.' in note will be lowercased to "
                              "'art. no.' by IEEEtran.bst; wrap as {{Art. no.}}" % key)
            issues += 1
        if re.search(r"xxxxxx", ent, re.I):
            fail("bib-style", "%s: placeholder 'xxxxxx' found in .bib entry" % key)
            issues += 1
    if issues == 0:
        ok("bib-style", "all .bib entries pass IEEEtran.bst field checks")


def check_bib_order(src, bib_path=None):
    """IEEE requires \\bibitem order == order of first citation in the body."""
    cut = src.find(r"\begin{thebibliography}")
    first = []
    body_for_cite = src[:cut] if cut >= 0 else src
    for m in re.finditer(r"\\cite\{([^}]*)\}", body_for_cite):
        for k in m.group(1).split(","):
            k = k.strip()
            if k and k not in first:
                first.append(k)

    if cut < 0:
        if bib_path and os.path.exists(bib_path):
            bibtxt = open(bib_path, encoding="utf-8", errors="replace").read()
            bib_keys = [m.group(2) for m in re.finditer(r"@(\w+)\{\s*([^,\s]+)\s*,", bibtxt) if m.group(1).lower() != "ieeetranbstctl"]
            extra_b = [k for k in bib_keys if k not in first]
            extra_c = [k for k in first if k not in bib_keys]
            if extra_b:
                fail("bib-file", "in .bib but never cited in body: %s" % extra_b)
            if extra_c:
                fail("bib-file", "cited in body but missing in .bib: %s" % extra_c)
            if not extra_b and not extra_c:
                ok("bib-file", "%d cited keys match .bib entries (BibTeX mode)" % len(first))
            check_bib_entries_quality(bibtxt)
        else:
            warn("bib", "no thebibliography environment found; pass --bib to check .bib")
        return
    body, bib = src[:cut], src[cut:]
    bib_order = [m.group(1) for m in re.finditer(r"\\bibitem\{([^}]*)\}", bib)]
    if first != bib_order:
        for i in range(max(len(first), len(bib_order))):
            a = first[i] if i < len(first) else "(none)"
            b = bib_order[i] if i < len(bib_order) else "(none)"
            if a != b:
                fail("bib-order", "render [%d]: first cited '%s' but \\bibitem '%s'" % (i + 1, a, b))
                break
        extra_b = [k for k in bib_order if k not in first]
        extra_c = [k for k in first if k not in bib_order]
        if extra_b:
            fail("bib-order", "in bibliography but never cited: %s" % extra_b)
        if extra_c:
            fail("bib-order", "cited but missing a \\bibitem: %s" % extra_c)
    else:
        ok("bib-order", "%d entries, order of first citation matches" % len(bib_order))

    # a new \\bibitem inserted mid-list silently renumbers everything after it
    if bib_path and os.path.exists(bib_path):
        bibtxt = open(bib_path, encoding="utf-8", errors="replace").read()
        bib_keys = [m.group(2) for m in re.finditer(r"@(\w+)\{\s*([^,\s]+)\s*,", bibtxt) if m.group(1).lower() != "ieeetranbstctl"]
        if bib_keys and set(bib_keys) != set(bib_order):
            fail("bib-file", "the .bib keys do not match the \\bibitem keys; "
                             "one of the two is stale (bib-only: %s; tex-only: %s)"
                 % (sorted(set(bib_keys) - set(bib_order)),
                    sorted(set(bib_order) - set(bib_keys))))
        elif bib_keys:
            ok("bib-file", "the .bib keys match the \\bibitem keys")
        check_bib_entries_quality(bibtxt)


def check_hardcoded_cites(src):
    hits = []
    for m in re.finditer(r"(?<![\w\[])\[(\d{1,3})(?:[,\-]\s*\d{1,3})*\](?![\w(])", src):
        hits.append((lineno(src, m.start()), m.group(0)))
    if hits:
        for l, t in hits:
            warn("hardcoded-cite", "L%d literal '%s' in the body; use \\cite so "
                                   "numbering stays automatic" % (l, t))
    else:
        ok("hardcoded-cite", "no literal citation numbers in the body")


def check_float_order(src):
    """Rendered figure/table numbers follow source order; the body must cite
    them in non-decreasing order, starting at 1."""
    def scan(envs, refword):
        order = []
        pat = r"\\begin\{(?:%s)\}" % "|".join(re.escape(e) for e in envs)
        for m in re.finditer(pat, src):
            seg = src[m.start():m.start() + 2000]
            lb = re.search(r"\\label\{([^}]*)\}", seg)
            order.append(lb.group(1) if lb else None)
        num = {lb: i + 1 for i, lb in enumerate(order) if lb}
        seq = []
        for m in re.finditer(re.escape(refword) + r"~?\\ref\{([^}]*)\}", src):
            lb = m.group(1)
            if lb in num:
                seq.append((lineno(src, m.start()), lb, num[lb]))
        return order, num, seq

    for envs, refword, name in ((["figure", "figure*"], "Fig.", "figure"),
                                (["table", "table*"], "Table", "table")):
        order, num, seq = scan(envs, refword)
        if not order:
            continue
        if len(order) != len([x for x in order if x]):
            fail("float:" + name, "some %s environments have no \\label" % name)
        nums = [n for _, _, n in seq]
        if not nums:
            warn("float:" + name, "no %s is referenced in the body" % name)
            continue
        if nums[0] != 1:
            fail("float:" + name, "the first %s reference in the body is %s %d, "
                                  "not 1" % (refword, refword, nums[0]))
        bad = [(seq[i], seq[i + 1]) for i in range(len(nums) - 1) if nums[i] > nums[i + 1]]
        if bad:
            (l1, lb1, n1), (l2, lb2, n2) = bad[0]
            fail("float:" + name, "%s %d is cited at L%d but %s %d at L%d: "
                                  "the references run out of order"
                 % (refword, n1, l1, refword, n2, l2))
        else:
            ok("float:" + name, "references run %s"
               % ",".join(str(n) for n in nums))
        cited = set()
        for _, lb, _ in seq:
            cited.add(lb)
        unused = [lb for lb in num if lb not in cited]
        if unused:
            fail("float:" + name, "never cited in the body: %s" % unused)
        print("    %s order (rendered number): %s"
              % (name, ", ".join("%d=%s" % (num[lb], lb) for lb in order if lb)))


def check_duplicate_expansions(src):
    """'spelled out (ABBR)' should not be expanded twice inside one region.

    The abstract and the body are read as separate units, so a paper is allowed
    to expand an acronym once in each: a reader who starts at the abstract never
    sees the body's definition, and vice versa. Two expansions inside the same
    region is still a defect.

    Only the body up to the bibliography is examined: an acronym inside a
    bibliography entry is part of a cited title, not the paper's own prose.
    """
    cut = src.find(r"\begin{thebibliography}")
    body = src[:cut] if cut >= 0 else src

    a0 = body.find(r"\begin{abstract}")
    a1 = body.find(r"\end{abstract}")
    k0 = body.find(r"\begin{IEEEkeywords}")
    k1 = body.find(r"\end{IEEEkeywords}")
    regions = []
    if a0 >= 0 and a1 > a0:
        regions.append(("abstract", a0, a1))
    else:
        a1 = -1
    if k0 >= 0 and k1 > k0:
        regions.append(("keywords", k0, k1))
    else:
        k1 = -1
    body_start = max(a1, k1) + 1 if max(a1, k1) >= 0 else 0
    regions.append(("body", body_start, len(body)))

    def region_of(pos):
        for name, s, e in regions:
            if s <= pos < e:
                return name
        return "body"

    pat = re.compile(r"([A-Za-z][A-Za-z\-]+(?:\s+[A-Za-z\-]+){0,5})\s+\(([A-Z]{2,7}s?)\)")
    seen = {}
    for m in pat.finditer(body):
        seen.setdefault(m.group(2), []).append(
            (lineno(body, m.start()), m.group(0), region_of(m.start())))

    duplicated = False
    for abbr, hits in sorted(seen.items()):
        per_region = {}
        for ln, txt, reg in hits:
            per_region.setdefault(reg, []).append(ln)
        for reg, lns in per_region.items():
            if len(lns) > 1:
                duplicated = True
                warn("abbr", "'%s' is expanded %d times in the %s (%s); one "
                             "expansion per region" % (abbr, len(lns), reg,
                                                       ", ".join("L%d" % x for x in lns)))
    if not duplicated:
        ok("abbr", "no acronym expanded twice within one region")

    # Within each region the acronym must be expanded before it is used bare.
    # The keyword list is exempt: it is a metadata tag list, not prose.
    for abbr, hits in sorted(seen.items()):
        for reg, s, e in regions:
            if reg == "keywords":
                continue
            first_expand = min((ln for ln, _, r in hits if r == reg), default=None)
            first_bare = None
            for m in re.finditer(r"(?<![A-Za-z])%s(?![a-z])" % re.escape(abbr), body[s:e]):
                if re.match(r"\s*\(", body[s + m.end():s + m.end() + 2]):
                    continue  # this occurrence is the expansion itself
                first_bare = lineno(body, s + m.start())
                break
            if first_bare is not None and (first_expand is None or first_bare < first_expand):
                fail("abbr", "'%s' is used bare at L%d in the %s but is not "
                             "expanded there" % (abbr, first_bare, reg))

    for abbr, hits in sorted(seen.items()):
        for reg, s, e in regions:
            for ln, txt, r in hits:
                if r == reg:
                    print("    %-6s expanded in %-8s L%-4d  \"%s\""
                          % (abbr, reg, ln, txt.strip()))
                    break





def check_article_number(src):
    """a/an before a number depends on how the number is pronounced."""
    VOWEL_SOUND = re.compile(r"^(8|11|18|80|800|8000|11000|18000)\b")
    hits = []
    for m in re.finditer(r"\b(a|an|A|An)\s+~?\$?([0-9][0-9,\.]*)", src):
        art, digits = m.group(1), m.group(2)
        head = digits.replace(",", "").split(".")[0]
        if VOWEL_SOUND.match(head):
            if art.lower() != "an":
                hits.append((lineno(src, m.start()), m.group(0), "should be 'an'"))
        else:
            if art.lower() == "an":
                hits.append((lineno(src, m.start()), m.group(0), "should be 'a'"))
    if hits:
        for l, t, fix in hits:
            warn("article", "L%d '%s' -> %s (depends on pronunciation, confirm)"
                 % (l, t, fix))
    else:
        ok("article", "a/an before numbers looks consistent")
    for m in re.finditer(r"\b(a|an)\s+[A-Z][A-Za-z]*", src):
        word = m.group(0)
        # nouns whose initial is a vowel letter but a consonant sound, and back
        if re.match(r"(?i)^(an)\s+([Uu]ni|[Uu]ser|[Oo]ne|[Ee]u)", word):
            warn("article", "L%d '%s' is usually 'a' (consonant sound)"
                 % (lineno(src, m.start()), word))
        if re.match(r"(?i)^(a)\s+([Hh]our|[Hh]onest|[Ss]?MPU|[Nn]VIDIA|[Ff]FT|[Xx]id)", word):
            warn("article", "L%d '%s' may need 'an' (vowel sound)"
                 % (lineno(src, m.start()), word))


def check_units(src):
    """A number and its unit should not be split across a line break."""
    hits = []
    for m in re.finditer(r"\d\s+(?=(?:mm|cm|km|MeV|keV|GeV|mA|A|W|V|Hz|kbps|GiB|GB|ns|us|ms|s|K|C)\b)", src):
        hits.append(lineno(src, m.start()))
    if hits:
        warn("units", "%d place(s) use a plain space between number and unit "
                      "(L%s); use ~ to keep them on one line"
             % (len(hits), ", ".join(str(x) for x in sorted(set(hits))[:10])))
    else:
        ok("units", "no bare space between number and unit")


def check_cjk_punctuation(src):
    bad = re.findall(r"[，。、；：（）【】“”‘’]", src)
    if bad:
        fail("punctuation", "%d full-width punctuation mark(s) in the LaTeX source" % len(bad))
    else:
        ok("punctuation", "no full-width punctuation")


# --- main -----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Static pre-submission checks for a LaTeX paper.")
    ap.add_argument("tex", help="path to the main .tex file")
    ap.add_argument("--bib", help="optional .bib file to cross-check keys against")
    ap.add_argument("--figdir", help="optional figures directory (relative to the .tex)")
    args = ap.parse_args()

    if not os.path.exists(args.tex):
        print("no such file: %s" % args.tex)
        return 2

    src = open(args.tex, encoding="utf-8", errors="replace").read()
    base = os.path.dirname(os.path.abspath(args.tex))

    print("=" * 78)
    print("paper-review static check: %s" % args.tex)
    print("characters: %d" % len(src))
    print("=" * 78)

    check_ascii(src)
    check_braces(src)
    check_dollars(src)
    check_cjk_punctuation(src)
    check_environments(src, ["figure", "figure*", "table", "table*", "tabular",
                             "thebibliography", "abstract", "IEEEkeywords"])
    check_graphics(src, base, args.figdir)
    check_text_math(src)
    check_bib_order(src, args.bib)
    check_hardcoded_cites(src)
    print()
    check_float_order(src)
    print()
    check_duplicate_expansions(src)
    check_article_number(src)
    check_units(src)

    print()
    print("-" * 78)
    for tag, msg in PASSES:
        print("PASS  %-14s %s" % (tag, msg))
    for tag, msg in WARNS:
        print("WARN  %-14s %s" % (tag, msg))
    for tag, msg in FAILS:
        print("FAIL  %-14s %s" % (tag, msg))
    print("-" * 78)
    print("%d fail, %d warn" % (len(FAILS), len(WARNS)))
    if WARNS:
        print("Warnings need a human decision: pronunciation, which term was "
              "introduced where, or facts the script cannot see.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
