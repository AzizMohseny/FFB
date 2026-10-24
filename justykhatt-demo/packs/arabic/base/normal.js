(function () {
  "use strict";

  const CFG = {
    maxAxis: 700,        // سقف خوانایی در Normal (۰..۱۰۰۰)
    center: 0.5, sigma: 0.22,
    wCenter: 1.0,        // نزدیکی به وسط ترکیب
    wNearEnd: 0.25,      // «سوم از آخر» فقط یک ترجیح
    wCarrier: 0.4,       // ظرفیت بیشتر = حامل بهتر
    wLength: 0.5,        // ترکیب بلندتر بهتر
    minScore: 0.35,      // زیر این امتیاز کشیده نمی‌شود
    targetFill: 0.5      // کلمه‌ها را تا این کسر از ظرفیت‌شان پر کن؛ کمتر = کلمهٔ بیشتر
  };

  // دسته‌های حرفی برای ممنوعیت‌ها؛ خودت کامل کن
  const CLASS = { beh: new Set("بپتثنیئ"), lam: new Set("ل"), meem: new Set("م") };

  // قواعد نانوشتهٔ خوشنویسی؛ هر فیلد اختیاری است. نمونه (غیرفعال):
  // { right: { cls: "lam", form: "init" }, left: { cls: "meem" } }
  const FORBIDDEN = [];

  const match = (spec, base, form) => !spec ||
    ((!spec.cls || CLASS[spec.cls].has(base)) && (!spec.form || spec.form === form));
  const isForbidden = p => FORBIDDEN.some(r =>
    match(r.right, p.rightBase, p.rightForm) && match(r.left, p.leftBase, p.leftForm));

  function score(p) {
    const r = (p.posInComp + 0.5) / (p.compLen - 1);      // موقعیت اتصال در ترکیب، ۰..۱
    const center = Math.exp(-Math.pow(r - CFG.center, 2) / (2 * CFG.sigma * CFG.sigma));
    const nearEnd = p.rightFromEnd === 3 ? 1 : 0;
    const carrier = Math.min(1, (p.rightGlyph.gain + p.leftGlyph.gain) / 1500);
    const length = Math.min(1, p.compLen / 6);
    const sum = CFG.wCenter + CFG.wNearEnd + CFG.wCarrier + CFG.wLength;
    return (CFG.wCenter * center + CFG.wNearEnd * nearEnd +
            CFG.wCarrier * carrier + CFG.wLength * length) / sum;
  }

  // حداکثر یک اتصال برای هر کلمه: بهترین امتیاز
  function bestPerWord(pairs) {
    const best = new Map();
    for (const p of pairs) {
      if (p.compLen < 3 || isForbidden(p)) continue;
      p.score = score(p);
      if (p.score < CFG.minScore) continue;
      p.max = Math.min(p.max, CFG.maxAxis);
      const k = p.lineIndex + ":" + p.wordIndex, cur = best.get(k);
      if (!cur || p.score > cur.score) best.set(k, p);
    }
    return [...best.values()];
  }

  // کلمه‌های بهتر اول، تا وقتی ظرفیتِ پرشدهٔ آن‌ها فضای باقیمانده را بپوشاند
  function chooseForLine(pairs, rest) {
    const chosen = []; let cap = 0;
    for (const p of pairs.sort((a, b) => b.score - a.score)) {
      chosen.push(p);
      cap += p.max * p.gainPx * CFG.targetFill;
      if (cap >= rest) break;
    }
    return chosen;
  }

  // مقدار محور یکسان برای همهٔ اتصال‌های انتخاب‌شده، با رعایت سقف
  function distribute(pairs, rest) {
    const v = new Map(pairs.map(p => [p, 0]));
    let free = pairs.slice();
    while (rest > 0.25 && free.length) {
      const total = free.reduce((s, p) => s + p.gainPx, 0);
      const head = Math.min(...free.map(p => p.max - v.get(p)));
      const step = Math.min(rest / total, head);
      free.forEach(p => v.set(p, v.get(p) + step));
      rest -= step * total;
      free = free.filter(p => v.get(p) < p.max - 1e-6);
    }
    return v;
  }

  // remainingSpace: عدد (برای همهٔ خط‌ها) یا { [lineIndex]: px }
  function generateCommands(tagData, lines, remainingSpace) {
    const upm = (window.FFBCaps && window.FFBCaps.upm) || 2300;
    const byLine = new Map();
    for (const p of bestPerWord(tagData.stretchPairs || [])) {
      if (!byLine.has(p.lineIndex)) byLine.set(p.lineIndex, []);
      byLine.get(p.lineIndex).push(p);
    }
    const commands = [];
    for (const [lineIndex, pairs] of byLine) {
      const rest = typeof remainingSpace === "number" ? remainingSpace : (remainingSpace[lineIndex] || 0);
      if (rest <= 0) continue;
      const fontSize = parseFloat(getComputedStyle(pairs[0].rightGlyph.node.parentElement).fontSize);
      pairs.forEach(p => { p.gainPx = (p.rightGlyph.gain + p.leftGlyph.gain) / 1000 * fontSize / upm; });
      const chosen = chooseForLine(pairs, rest);
      const v = distribute(chosen, rest);
      for (const p of chosen) {
        const value = v.get(p);
        if (!(value > 0)) continue;
        for (const g of [p.rightGlyph, p.leftGlyph]) {          // هر دو گلیف به یک اندازه
          commands.push({ type: "stretch", lineIndex, wordIndex: p.wordIndex, charIndex: g.charIndex,
            sourceStart: g.sourceStart, sourceEnd: g.sourceEnd, node: g.node,
            axisName: g.axis, value });
        }
      }
    }
    return commands;
  }

  window.BaseNormalRulePack = { generateCommands };
})();