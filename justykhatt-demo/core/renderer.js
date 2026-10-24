(function () {
  "use strict";

  function clear(root) {
    root.querySelectorAll("span[data-jk]").forEach(s => s.replaceWith(...s.childNodes));
    root.normalize();
  }

  function applyCommands(root, commands) {
    if (!commands || !commands.length) return;
    const targets = new Map();
    for (const c of commands) {
      if (!c.node || !(c.axisName || c.feature || c.type === "spacing")) continue;
      if (!targets.has(c.node)) targets.set(c.node, new Map());
      const m = targets.get(c.node), key = c.sourceStart + ":" + c.sourceEnd;
      if (!m.has(key)) m.set(key, { start: c.sourceStart, end: c.sourceEnd, axes: {}, features: {}, spacing: 0 });
      const t = m.get(key);
      if (c.axisName) t.axes[c.axisName] = c.value ?? 0;
      else if (c.feature) t.features[c.feature] = c.value ?? 1;
      else t.spacing = c.delta;
    }
    for (const [node, m] of targets) {
      [...m.values()].sort((a, b) => b.start - a.start).forEach(t => {
        const r = document.createRange();
        r.setStart(node, t.start); r.setEnd(node, t.end);
        const span = document.createElement("span");
        span.dataset.jk = "1";
        const fvs = Object.entries(t.axes).map(([a, v]) => `'${a}' ${v.toFixed(1)}`).join(", ");
        const fts = Object.entries(t.features).map(([k, v]) => `"${k}" ${v}`).join(", ");
        if (fvs) span.style.fontVariationSettings = fvs;
        if (fts) span.style.fontFeatureSettings = fts;
        if (t.spacing) span.style.wordSpacing = t.spacing.toFixed(2) + "px";
        r.surroundContents(span);
      });
    }
  }

  window.RendererEngine = { applyCommands, clear };
})();