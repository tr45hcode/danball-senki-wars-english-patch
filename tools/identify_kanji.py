#!/usr/bin/env python3
"""Identify per-file glyph bitmaps (mostly kanji) using the furigana.

Usage: identify_kanji.py <extracted/cpk> <out.tsv>

For every unique glyph bitmap:
  1. visual score against every JIS X 0208 character (glyphmatch),
  2. reading evidence: for each furigana group the glyph appears in, the set
     of kanji (from KANJIDIC2) that can spell its share of the reading
     (allowing rendaku and small-tsu changes at group-internal boundaries),
  3. a small prior for frequent kanji.
Groups are re-solved with confidently identified glyphs fixed, so evidence
propagates between glyphs.

Output columns: key, cell, char, status, score, support, top5, uses
  status: word    furigana compounds match dictionary words (JMdict)
          ruby    furigana matches the kanji's readings (KANJIDIC2)
          aligned copied from the 14 px twin of a small-font message file
          visual  no usable reading evidence, best visual match
"""
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glyphmatch  # noqa: E402
import jmdict  # noqa: E402
import kanjidic  # noqa: E402
from ctrtex import decode_l8  # noqa: E402
from dump_text import glyph_key, rmd_pairs  # noqa: E402
from rmd import GLOBAL_CHARS, LOCAL_BASE, Rmd, ruby_reading  # noqa: E402

MAX_SEG = 8
VOICED = dict(zip('かきくけこさしすせそたちつてとはひふへほ', 'がぎぐげござじずぜぞだぢづでどばびぶべぼ'))
VOICED.update(zip('はひふへほ', 'ぱぴぷぺぽ'))
UNVOICE = defaultdict(list)
for k, v in VOICED.items():
    UNVOICE[v].append(k)
UNVOICE['じ'].append('ち')
UNVOICE['ず'].append('つ')


def hira(s):
    return kanjidic.kata_to_hira(s)


def base_forms(seg, first, last):
    """Dictionary readings that could surface as `seg` inside a group."""
    forms = {seg}
    if not first and seg and seg[0] in UNVOICE:
        forms |= {u + seg[1:] for u in UNVOICE[seg[0]]}
    if not last and seg.endswith('っ'):
        forms |= {f[:-1] + t for f in list(forms) for t in 'つくちき'}
    return forms


class Readings:
    def __init__(self, repertoire):
        dic = kanjidic.load()
        self.primary = defaultdict(set)
        self.names = defaultdict(set)
        self.freq = {}
        for ch, (readings, names, freq) in dic.items():
            if ch not in repertoire:
                continue
            self.freq[ch] = freq
            for r in readings:
                self.primary[r].add(ch)
            for r in names:
                self.names[r].add(ch)

    def kanji_for(self, seg, first, last, use_names):
        out = set()
        for f in base_forms(seg, first, last):
            out |= self.primary.get(f, set())
            if use_names:
                out |= self.names.get(f, set())
        return out


def collect(root):
    """Unique glyph bitmaps, their use counts, and furigana groups."""
    glyphs = {}                      # key -> [cell, bitmap]
    uses = Counter()
    groups = Counter()               # (items tuple, reading) -> count
    layouts = {}                     # rmd path -> (cell, {message id: token signature, local keys})
    for p, t in rmd_pairs(root):
        r = Rmd(open(p, 'rb').read())
        atlas = decode_l8(open(t, 'rb').read()[0x1E0:], r.atlas_w, r.atlas_h)
        keys = []
        for k in range(r.glyph_count - 297):
            rect, w = r.glyph_rect(k)
            if not w:
                keys.append(None)
                continue
            bm = atlas.crop(rect)
            key = glyph_key(r.cell, bm)
            glyphs.setdefault(key, [r.cell, bm])
            keys.append(key)
        layouts[p] = (r.cell, {})
        for mid, off, _, _ in r.messages():
            ruby, items = None, []
            sig, local = [], []
            done = []          # [items, reading, okurigana collected so far, still collecting]
            for tok in r.tokens(off):
                sig.append(('L' if tok[0] == 'g' and tok[1] >= LOCAL_BASE else tok[:2]))
                ch = GLOBAL_CHARS[tok[1] - 1] if tok[0] == 'g' and 1 <= tok[1] <= 297 else None
                # hiragana directly after a group is its okurigana (verb/adjective ending)
                if done and done[-1][3]:
                    if ch is not None and 'ぁ' <= ch <= 'ゖ' and len(done[-1][2]) < 4:
                        done[-1][2] += ch
                    elif not (tok[0] == 'ctl' and tok[1] == 0x11):
                        done[-1][3] = False
                if tok[0] == 'g':
                    v = tok[1]
                    if v >= LOCAL_BASE:
                        key = keys[v - LOCAL_BASE] if v - LOCAL_BASE < len(keys) else None
                        item = ('k', key)
                        local.append(key)
                        if key:
                            uses[key] += 1
                    else:
                        item = ('c', ch or '?')
                    if ruby is not None:
                        items.append(item)
                elif tok[1] == 0x10:
                    ruby, items = ruby_reading(tok[2]), []
                elif tok[1] == 0x11 and ruby is not None:
                    if items and all(i[1] for i in items):
                        done.append([tuple(items), ruby, '', True])
                    ruby = None
            for items_, ruby_, okuri, _ in done:
                groups[(items_, ruby_, okuri)] += 1
            layouts[p][1][mid] = (tuple(sig), local)
    return glyphs, uses, groups, layouts


def align_small_fonts(layouts, result):
    """Small-font (10/11 px) RMDs that repeat a 14 px RMD message for message
    inherit the 14 px identifications, which are far more reliable."""
    big = {p: msgs for p, (cell, msgs) in layouts.items() if cell == 14}
    votes = defaultdict(Counter)
    for p, (cell, msgs) in layouts.items():
        if cell == 14 or not msgs:
            continue
        for q, bmsgs in big.items():
            if bmsgs.keys() != msgs.keys() or any(bmsgs[m][0] != msgs[m][0] for m in msgs):
                continue
            for m, (_, local) in msgs.items():
                for small_key, big_key in zip(local, bmsgs[m][1]):
                    if small_key and big_key and big_key in result:
                        votes[small_key][result[big_key][0]] += 1
            break
    for key, c in votes.items():
        ch, n = c.most_common(1)[0]
        if n >= 0.8 * sum(c.values()):
            result[key] = (ch, 'aligned', 1.0, n / sum(c.values()), 1.0)
    return len(votes)


def solve_group(items, reading, fixed, readings, use_names):
    """Return {item index: set of kanji} that occur in some full segmentation."""
    n, R = len(items), reading
    # options[i][pos] -> list of (length, candidate set or None for a known char)
    options = [defaultdict(list) for _ in range(n)]
    for i, (kind, val) in enumerate(items):
        first, last = i == 0, i == n - 1
        for pos in range(len(R)):
            if kind == 'c' or val in fixed:
                ch = val if kind == 'c' else fixed[val]
                if kind == 'c' and not ('ぁ' <= ch <= 'ヶ' or ch == 'ー'):
                    return None
                if kind == 'c':
                    if R.startswith(hira(ch), pos):
                        options[i][pos].append((len(ch), None))
                    continue
                for L in range(1, min(MAX_SEG, len(R) - pos) + 1):
                    if ch in readings.kanji_for(R[pos:pos + L], first, last, use_names):
                        options[i][pos].append((L, None))
                continue
            for L in range(1, min(MAX_SEG, len(R) - pos) + 1):
                cands = readings.kanji_for(R[pos:pos + L], first, last, use_names)
                if cands:
                    options[i][pos].append((L, cands))
    fwd = [set() for _ in range(n + 1)]
    fwd[0].add(0)
    for i in range(n):
        for pos in fwd[i]:
            for L, _ in options[i].get(pos, ()):
                fwd[i + 1].add(pos + L)
    if len(R) not in fwd[n]:
        return None
    bwd = [set() for _ in range(n + 1)]
    bwd[n].add(len(R))
    for i in range(n - 1, -1, -1):
        for pos, opts in options[i].items():
            if any(pos + L in bwd[i + 1] for L, _ in opts):
                bwd[i].add(pos)
    out = {}
    for i in range(n):
        if items[i][0] != 'k' or items[i][1] in fixed:
            continue
        s = set()
        for pos in fwd[i] & bwd[i]:
            for L, cands in options[i].get(pos, ()):
                if cands and pos + L in bwd[i + 1]:
                    s |= cands
        out[i] = s
    return out


def visual_scores(glyphs, cells):
    """{cell: (chars, {key: score vector})} over the JIS repertoire."""
    out = {}
    for cell in cells:
        chars, mat, prior = glyphmatch.build_reference(cell)
        keys = [k for k, g in glyphs.items() if g[0] == cell]
        S, U = glyphmatch.SHIFT, glyphmatch.UP
        shifts = [(dy, dx) for dy in range(-S * U, S * U + 1, U) for dx in range(-S * U, S * U + 1, U)]
        mat_t = np.ascontiguousarray(mat.T.astype(np.float32))
        scores = {}
        for b in range(0, len(keys), 128):
            batch = keys[b:b + 128]
            vecs = []
            for k in batch:
                a = glyphmatch._prep(glyphs[k][1], cell)
                vecs += [glyphmatch._unit(np.roll(np.roll(a, dy, 0), dx, 1)).ravel() for dy, dx in shifts]
            s = (np.stack(vecs).astype(np.float32) @ mat_t).reshape(len(batch), len(shifts), -1).max(axis=1)
            for k, row in zip(batch, s):
                scores[k] = row
        out[cell] = (chars, scores)
        print(f'cell {cell}: {len(keys)} glyphs scored', file=sys.stderr)
    return out


def word_matches(items, reading, fixed, words, okuri=''):
    """Dictionary words with this reading whose spelling fits the group.

    Compounds are matched as they stand. A group followed by okurigana is
    also tried with 1..len(okuri) of those kana appended (逃|に + げる ->
    にげる = 逃げる); only the part covered by the group is returned.
    """
    if len(items) > 1:
        out = _match(items, reading, fixed, words)
        if out:
            return out
    for n in range(len(okuri), 0, -1):
        tail = okuri[:n]
        out = [w[:-n] for w in _match(items, reading + tail, fixed, words, tail)]
        if out:
            return out
    return []


def _match(items, reading, fixed, words, tail=''):
    out = []
    for w in words.get(reading, ()):
        if len(w) != len(items) + len(tail) or (tail and not w.endswith(tail)):
            continue
        ok = True
        for (kind, val), ch in zip(items, w):
            known = val if kind == 'c' else fixed.get(val)
            if known is not None and hira(known) != hira(ch):
                ok = False
                break
        if ok:
            out.append(w)
    return out


VISUAL_SLACK = 0.20   # a reading-backed candidate may look at most this much worse


def identify(glyphs, uses, groups, vis, rounds=3):
    any_chars = next(iter(vis.values()))[0]
    readings = Readings(set(any_chars))
    words = jmdict.load()
    index = {cell: {c: i for i, c in enumerate(chars)} for cell, (chars, _) in vis.items()}

    def prior(ch):
        if ch not in readings.freq:
            return 0.0                      # not a kanji
        f = readings.freq[ch]
        return 0.04 * max(0.0, 1 - f / 2500) if f else -0.03   # unranked = rare

    group_list = list(groups.items())
    fixed, result = {}, {}
    for rnd in range(rounds):
        support, word_sup = defaultdict(Counter), defaultdict(Counter)
        occ, word_occ = Counter(), Counter()
        for (items, reading, okuri), _ in group_list:
            # each distinct group counts once: a name tag repeated in hundreds
            # of scenes (瀬名|せな, which JMdict also spells 背中) must not
            # outvote the other contexts a glyph appears in
            count = 1
            sol = solve_group(items, reading, fixed, readings, use_names=False)
            if sol is None:
                sol = solve_group(items, reading, fixed, readings, use_names=True)
            # a single glyph alone is rarely a dictionary word (負|ま + けて is a
            # verb stem), so it only gets word evidence through its okurigana
            matches = word_matches(items, reading, fixed, words, okuri)
            for i, (kind, key) in enumerate(items):
                if kind != 'k' or key in fixed:
                    continue
                occ[key] += count
                if sol is not None:
                    for ch in sol.get(i, ()):
                        support[key][ch] += count
                if matches:
                    word_occ[key] += count
                    for ch in {w[i] for w in matches}:
                        word_sup[key][ch] += count

        # ranked candidates per glyph
        ranked = {}
        for key, (cell, _) in glyphs.items():
            if key in fixed:
                continue
            chars, scores = vis[cell]
            vec = scores[key]
            best_vis = float(vec.max())
            opts = []
            if word_occ[key]:
                top_share = max(s for s in word_sup[key].values()) / word_occ[key]
                for c, s in word_sup[key].items():
                    share = s / word_occ[key]
                    if c in index[cell] and share >= top_share - 0.15 and \
                            vec[index[cell][c]] >= best_vis - VISUAL_SLACK:
                        opts.append((float(vec[index[cell][c]]) + 0.10 * share + prior(c), c, 'word', share))
            if not opts and occ[key]:
                cands = [(c, s / occ[key]) for c, s in support[key].items() if c in index[cell]]
                top_share = max((s for _, s in cands), default=0)
                if top_share >= 0.5:
                    for c, share in cands:
                        if share >= top_share - 0.25 and vec[index[cell][c]] >= best_vis - VISUAL_SLACK:
                            opts.append((float(vec[index[cell][c]]) + 0.10 * share + prior(c), c, 'ruby', share))
            if not opts:
                order = np.argsort(-vec)[:20]
                opts = [(float(vec[i]) + prior(chars[i]), chars[i], 'visual', 0.0) for i in order]
            ranked[key] = sorted(opts, reverse=True)

        # note: the same character can have several bitmaps (e.g. 名 has three
        # 14 px renderings across files), so characters are not exclusive
        new_fixed = {}
        for key, opts in ranked.items():
            sc, ch, status, share = opts[0]
            margin = sc - opts[1][0] if len(opts) > 1 else 1.0
            result[key] = (ch, status, sc, share, margin)
            if (status == 'word' and share >= 0.6 and margin > 0.02) or \
               (status == 'ruby' and share >= 0.8 and (margin > 0.03 or len(opts) == 1)):
                new_fixed[key] = ch
        fixed.update(new_fixed)
        print(f'round {rnd + 1}: {len(fixed)} glyphs fixed', file=sys.stderr)
    for key, ch in fixed.items():
        if key not in result:
            result[key] = (ch, 'word', 1.0, 1.0, 1.0)
    return result


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    root, out = sys.argv[1], sys.argv[2]
    glyphs, uses, groups, layouts = collect(root)
    print(f'{len(glyphs)} glyphs, {len(groups)} distinct furigana groups', file=sys.stderr)
    vis = visual_scores(glyphs, sorted({g[0] for g in glyphs.values()}))
    result = identify(glyphs, uses, groups, vis)
    n = align_small_fonts(layouts, result)
    print(f'{n} small-font glyphs aligned to their 14 px twins', file=sys.stderr)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('key\tcell\tchar\tstatus\tscore\tsupport\ttop5\tuses\n')
        for key in sorted(glyphs, key=lambda k: -uses[k]):
            ch, status, sc, share, _ = result[key]
            chars, scores = vis[glyphs[key][0]]
            top5 = ''.join(chars[i] for i in np.argsort(-scores[key])[:5])
            f.write(f'{key}\t{glyphs[key][0]}\t{ch}\t{status}\t{sc:.3f}\t{share:.2f}\t{top5}\t{uses[key]}\n')
    stats = Counter(r[1] for r in result.values())
    print(f'wrote {out}: {dict(stats)}', file=sys.stderr)


if __name__ == '__main__':
    main()
