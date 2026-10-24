(function () {
  "use strict";
  
  const CLASS = { beh: new Set("بپتثنیئ"), lam: new Set("ل"), meem: new Set("م") };
  const FORBIDDEN = [];

  const match = (s, base, form) => !s ||
    ((!s.cls || CLASS[s.cls].has(base)) && (!s.form || s.form === form));
  
  const isForbidden = p => FORBIDDEN.some(r =>
    match(r.right, p.rightBase, p.rightForm) && match(r.left, p.leftBase, p.leftForm));

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

  function lineWidths(words) {
    const box = new Map();
    for (const w of words || []) for (const c of w.chars || []) {
      const r = document.createRange();
      r.setStart(c.node, c.sourceStart); r.setEnd(c.node, c.sourceEnd);
      const b = r.getBoundingClientRect();
      const cur = box.get(w.lineIndex) || { l: Infinity, r: -Infinity };
      cur.l = Math.min(cur.l, b.left); cur.r = Math.max(cur.r, b.right);
      box.set(w.lineIndex, cur);
    }
    const out = {}; box.forEach((v, k) => { out[k] = v.r - v.l; });
    return out;
  }

  function spaceShrink(spaces, deficit, targetWidth, cfg) {
    if (!cfg.enabled || !spaces.length || !(deficit > 0)) return null;
    if (deficit > cfg.maxRatio * targetWidth) return null;
    const per = deficit / spaces.length;
    if (per > Math.min(...spaces.map(s => s.px * (1 - cfg.minFactor)))) return null;
    return spaces.map(s => ({ node: s.node, sourceStart: s.sourceStart, sourceEnd: s.sourceEnd, delta: -per }));
  }

  function xOf(g) {
    const r = document.createRange();
    r.setStart(g.node, g.sourceStart); r.setEnd(g.node, g.sourceEnd);
    const b = r.getBoundingClientRect();
    return (b.left + b.right) / 2;
  }

  window.ArabicKit = { 
    CLASS, 
    FORBIDDEN, 
    isForbidden, 
    distribute, 
    xOf, 
    lineWidths, 
    spaceShrink 
  };
})();