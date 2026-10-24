(function () {
  "use strict";
  const K = window.ArabicKit;

  const CFG = {
    // کشیدهٔ محوری برای پر کردن فضا
    wordsPerKashida: 3, maxAxis: 1000, minCompLen: 4,
    center: 0.5, sigma: 0.2, wCenter: 1, wCarrier: 0.5, wLength: 0.6,
    islandDx: 1.8, islandDecay: [1, 0.5], maxRun: 2,
    // سواش برای زیبایی
    wordsPerSwash: 5, swashWindow: 2, shrinkGap: 2, longEm: 0.1,
    // کوچک‌کردن اسپیس‌ها (امکان اختیاری)
    spaceShrink: { enabled: true, maxRatio: 0.05, minFactor: 0.55 },
    safetyPx: 0.75, minScore: 0.35, skipLastLine: true
  };

  function style(r, compLen, carrier) {
    const center = Math.exp(-Math.pow(r - CFG.center, 2) / (2 * CFG.sigma * CFG.sigma));
    const length = Math.min(1, compLen / 7);
    return (CFG.wCenter * center + CFG.wCarrier * carrier + CFG.wLength * length) /
           (CFG.wCenter + CFG.wCarrier + CFG.wLength);
  }

  function buildCandidates(tag, upm) {
    const axis = [], swash = [];
    const fsOf = g => parseFloat(getComputedStyle(g.node.parentElement).fontSize);
    for (const p of tag.stretchPairs || []) {
      if (p.compLen < CFG.minCompLen || K.isForbidden(p)) continue;
      const fs = fsOf(p.rightGlyph), g = p.rightGlyph.gain + p.leftGlyph.gain;
      axis.push({ lineIndex: p.lineIndex, wordIndex: p.wordIndex, fs,
        score: style((p.posInComp + 0.5) / (p.compLen - 1), p.compLen, Math.min(1, g / 1500)),
        glyphs: [p.rightGlyph, p.leftGlyph], x: K.xOf(p.rightGlyph),
        gainPx: g / 1000 * fs / upm, max: Math.min(p.max, CFG.maxAxis) });
    }
    for (const s of tag.swashes || []) {
      if (K.isForbidden(s)) continue;
      const fs = fsOf(s.glyph), px = s.glyph.gain * fs / upm;     // علامت‌دار
      const r = s.tail ? 0.5 : (s.posInComp + 0.5) / Math.max(1, s.compLen - 1);
      swash.push({ lineIndex: s.lineIndex, wordIndex: s.wordIndex, fs, px,
        long: px >= CFG.longEm * fs, glyphs: [s.glyph], x: K.xOf(s.glyph),
        style: style(r, s.compLen, Math.max(0, Math.min(1, px / fs))) });
    }
    return { axis, swash };
  }

  const featureCmd = (li, c) => {
    const g = c.glyphs[0];
    return { type: "feature", lineIndex: li, wordIndex: c.wordIndex, charIndex: g.charIndex,
      sourceStart: g.sourceStart, sourceEnd: g.sourceEnd, node: g.node, feature: g.feature, value: 1 };
  };

  function generateCommands(tagData, lines, remainingSpace, ctx) {
    const T = (ctx && ctx.targetWidth) || 0;
    const upm = (window.FFBCaps && window.FFBCaps.upm) || 2300;
    const { axis, swash } = buildCandidates(tagData, upm);
    const group = arr => {
      const m = new Map();
      arr.forEach(c => { if (!m.has(c.lineIndex)) m.set(c.lineIndex, []); m.get(c.lineIndex).push(c); });
      return m;
    };
    const axisBy = group(axis), swashBy = group(swash), spacesBy = group(tagData.spaces || []);

    const commands = []; commands.leftover = {}; commands.infeasible = false;
    const prevXs = [[], []];
    let run = 0, lastPara = null, gpos = 0, lastSwash = 0;
    const shift = xs => { prevXs[1] = prevXs[0]; prevXs[0] = xs; };

    for (const line of lines || []) {
      const li = line.lineIndex, words = line.words || [];
      const pos = new Map(words.map((w, i) => [w.wordIndex, gpos + i]));
      const P = c => (pos.has(c.wordIndex) ? pos.get(c.wordIndex) : c.wordIndex);
      const lineStart = gpos; gpos += words.length;
      if (line.paragraphIndex !== undefined && line.paragraphIndex !== lastPara) {
        prevXs[0] = []; prevXs[1] = []; run = 0; lastPara = line.paragraphIndex; lastSwash = lineStart;
      }
      if (CFG.skipLastLine && line.isLast) { shift([]); run = 0; continue; }

      const rem = typeof remainingSpace === "number" ? remainingSpace : (remainingSpace[li] || 0);
      let budget = rem >= 0 ? Math.max(0, rem - CFG.safetyPx) : rem - CFG.safetyPx;
      const xs = [];
      const sw = (swashBy.get(li) || []).slice().sort((a, b) => P(a) - P(b));
      const fs = (sw[0] || (axisBy.get(li) || [])[0] || { fs: 16 }).fs;

      const island = c => {
        let p = 0;
        prevXs.forEach((px, k) => px.forEach(x => {
          const d = Math.abs(c.x - x) / fs;
          if (d < CFG.islandDx) p += CFG.islandDecay[k] * (1 - d / CFG.islandDx);
        }));
        return Math.min(1, p);
      };

      // ۱) سواش برای زیبایی: تراکم یکی در هر wordsPerSwash کلمه
      sw.forEach(c => { c.adj = c.long ? c.style * (1 - 0.8 * island(c)) : c.style; });
      const fits = c => c.px <= 0 || c.px <= budget;
      const fit = c => (budget < 0 ? (c.px < 0 ? 0.4 : 0) : (c.px > 0 ? 0.15 : -0.05));
      const chosenSw = [];
      for (const s0 of sw) {
        const p0 = P(s0);
        if (p0 - lastSwash < CFG.wordsPerSwash) continue;
        const win = sw.filter(c => P(c) >= p0 && P(c) <= p0 + CFG.swashWindow &&
                                   c.adj >= CFG.minScore && fits(c));
        if (!win.length) continue;
        const best = win.reduce((a, b) => (b.adj + fit(b) > a.adj + fit(a) ? b : a));
        chosenSw.push(best); budget -= best.px; lastSwash = P(best);
      }
      // خط هنوز بلند است: سواش‌های کوتاه‌کننده با تراکم شل‌تر
      if (budget < 0) {
        const neg = sw.filter(c => c.px < 0 && !chosenSw.includes(c)).sort((a, b) => a.px - b.px);
        for (const c of neg) {
          if (budget >= 0) break;
          if (chosenSw.some(o => Math.abs(P(o) - P(c)) < CFG.shrinkGap)) continue;
          chosenSw.push(c); budget -= c.px;
        }
      }
      for (const c of chosenSw) { commands.push(featureCmd(li, c)); if (c.long) xs.push(c.x); }

      // ۲) هنوز بلند است: اسپیس‌ها را یکنواخت کوچک کن (اگر مجاز و شدنی)
      if (budget < 0) {
        const sp = K.spaceShrink(spacesBy.get(li) || [], -budget, T, CFG.spaceShrink);
        if (sp) {
          sp.forEach(s => commands.push({ type: "spacing", lineIndex: li, node: s.node,
            sourceStart: s.sourceStart, sourceEnd: s.sourceEnd, delta: s.delta }));
          budget = 0;
        } else { commands.infeasible = true; commands.leftover[li] = budget; shift(xs); run = 0; continue; }
      }

      // ۳) جا هست: کشیدهٔ محوری، کم‌تعداد و بلند، با پرهیز از جزیره
      const al = axisBy.get(li) || [];
      if (budget > 0.5 && al.length) {
        al.forEach(c => { c.adj = c.score * (1 - 0.8 * island(c)) * (run >= CFG.maxRun ? 0.6 : 1); });
        const best = new Map();
        al.forEach(c => { const cur = best.get(c.wordIndex); if (!cur || c.adj > cur.adj) best.set(c.wordIndex, c); });
        const ranked = [...best.values()].filter(c => c.adj >= CFG.minScore).sort((a, b) => b.adj - a.adj);
        const target = Math.max(1, Math.floor((words.length || best.size) / CFG.wordsPerKashida));
        const chosen = [];
        const gapOk = (c, gap) => chosen.every(o => Math.abs(P(o) - P(c)) >= gap);
        for (const c of ranked) {
          if (chosen.length >= target) break;
          if (gapOk(c, CFG.wordsPerKashida)) chosen.push(c);
        }
        const cap = () => chosen.reduce((s, c) => s + c.gainPx * c.max, 0);
        for (const gap of [CFG.wordsPerKashida, 2, 1]) {
          if (cap() >= budget) break;
          for (const c of ranked) {
            if (chosen.includes(c) || !gapOk(c, gap)) continue;
            chosen.push(c);
            if (cap() >= budget) break;
          }
        }
        const v = chosen.length ? K.distribute(chosen, budget) : new Map();
        let used = 0;
        for (const c of chosen) {
          const value = v.get(c) || 0;
          if (!(value > 0)) continue;
          used += value * c.gainPx; xs.push(c.x);
          for (const g of c.glyphs) commands.push({ type: "stretch", lineIndex: li, wordIndex: c.wordIndex,
            charIndex: g.charIndex, sourceStart: g.sourceStart, sourceEnd: g.sourceEnd, node: g.node,
            axisName: g.axis, value });
        }
        budget -= used;
      }
      if (budget > 0.5) commands.leftover[li] = budget;
      shift(xs);
      run = xs.length ? run + 1 : 0;
    }
    return commands;
  }

  window.ArtisticRulePack = { generateCommands };
})();
