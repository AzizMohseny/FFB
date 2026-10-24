(function () {
  "use strict";
  const ZWNJ = "\u200C";
  const AXIS_MAX = 1000;

  const baseOf = c => [...c.char].find(ch => ch !== ZWNJ && !/\p{M}/u.test(ch)) || "";
  
  // حروفی که به حرف بعدی وصل نمی‌شوند
  const NON_LEFT_JOINING = new Set("آأإٱادذرزژوؤةۀء"); 
  const endsComposition = c => c.char.includes(ZWNJ) || NON_LEFT_JOINING.has(baseOf(c));
  
  const formOf = (pos, len) => len === 1 ? "isol" : pos === 0 ? "init" : pos === len - 1 ? "fina" : "medi";

  function compositions(chars) {
    const out = []; let cur = [];
    chars.forEach((c, i) => {
      if (c.char === ZWNJ) { if (cur.length) { out.push(cur); cur = []; } return; }
      cur.push(i);
      if (endsComposition(c)) { out.push(cur); cur = []; }
    });
    if (cur.length) out.push(cur);
    return out;
  }

  function tagText(words, config) {
    const caps = (window.FFBCaps && window.FFBCaps.caps) || {};
    const swashTbl = (window.FFBCaps && window.FFBCaps.swash) || {};
    
    const gain = (c, form, axis) => (caps[baseOf(c)] && caps[baseOf(c)][form] && caps[baseOf(c)][form][axis]) || 0;
    
    const glyph = (c, axis, g) => ({ 
        charIndex: c.charIndex, 
        sourceStart: c.sourceStart,
        sourceEnd: c.sourceEnd, 
        node: c.node, 
        axis, 
        gain: g 
    });

    const stretchPairs = [];  
    const swashes = [];

    for (const word of words || []) {
      const chars = word.chars || [];
      compositions(chars).forEach((comp, compIndex) => {
        const len = comp.length;
        
        // ۱. پیدا کردن سواش‌ها
        for (let a = 0; a < len; a++) {
          const c = chars[comp[a]];
          const base = baseOf(c);
          const form = formOf(a, len);
          const swashEntry = swashTbl[base] && swashTbl[base][form];
          
          if (swashEntry && swashEntry[1]) {
            swashes.push({ 
              lineIndex: word.lineIndex, 
              wordIndex: word.wordIndex, 
              compIndex,
              compLen: len, 
              posInComp: a, 
              tail: form === "fina" || form === "isol",
              rightBase: base, 
              rightForm: form,
              glyph: { 
                charIndex: c.charIndex, 
                sourceStart: c.sourceStart, 
                sourceEnd: c.sourceEnd,
                node: c.node, 
                feature: swashEntry[1], 
                gain: swashEntry[0] 
              } 
            });
          }
        }

        // ۲. پیدا کردن جفت‌های کشیدگی (قانون طلایی)
        for (let a = 0; a < len - 1; a++) {
          const A = chars[comp[a]], B = chars[comp[a + 1]];
          const gA = gain(A, formOf(a, len), 0); // LEXP برای A
          const gB = gain(B, formOf(a + 1, len), 1); // REXP برای B
          
          if (gA > 0 && gB > 0) {
            stretchPairs.push({ 
              lineIndex: word.lineIndex, 
              wordIndex: word.wordIndex, 
              compLen: len, 
              posInComp: a, 
              compIndex, 
              rightFromEnd: len - a,
              rightGlyph: glyph(A, "LEXP", gA), 
              leftGlyph: glyph(B, "REXP", gB), 
              max: AXIS_MAX 
            });
          }
        }
      });
    }

    // ۳. پیدا کردن اسپیس‌ها (برای کوچک کردن در صورت نیاز)
    const spaces = [];
    const wl = (words || []).filter(w => w.chars && w.chars.length);
    for (let i = 0; i < wl.length - 1; i++) {
      if (wl[i].lineIndex !== wl[i + 1].lineIndex) continue;
      const a = wl[i].chars[wl[i].chars.length - 1], b = wl[i + 1].chars[0];
      if (a.node !== b.node || b.sourceStart <= a.sourceEnd) continue;
      
      const r = document.createRange();
      r.setStart(a.node, a.sourceEnd); 
      r.setEnd(a.node, b.sourceStart);
      spaces.push({ 
        lineIndex: wl[i].lineIndex, 
        node: a.node,
        sourceStart: a.sourceEnd, 
        sourceEnd: b.sourceStart, 
        px: r.getBoundingClientRect().width 
      });
    }

    return { 
      stretchOpportunities: [], 
      stretchPairs, 
      swashes, 
      spaces, 
      verticalOpportunities: [],
      substitutions: [], 
      allOpportunities: stretchPairs 
    };
  }

  window.TaggerEngine = { tagText };
})();