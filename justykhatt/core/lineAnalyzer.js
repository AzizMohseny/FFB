(function () {
  "use strict";

  const segmenter = new Intl.Segmenter("fa", { granularity: "grapheme" });

  function getTextNodes(root) {
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) nodes.push(walker.currentNode);
    return nodes;
  }

  function collectUnits(root) {
    const units = [];
    for (const node of getTextNodes(root)) {
      const text = node.nodeValue || "";
      for (const part of segmenter.segment(text)) {
        const start = part.index;
        const end = start + part.segment.length;
        const range = document.createRange();
        range.setStart(node, start);
        range.setEnd(node, end);
        const rects = Array.from(range.getClientRects());
        const rect = rects[0] || null;
        if (!rect) continue;
        units.push({
          text: part.segment,
          node,
          start,
          end,
          rect,
          lineKey: Math.round(rect.top * 2) / 2
        });
      }
    }
    return units;
  }

  function analyzeLines(root) {
    if (!(root instanceof Element)) {
      throw new TypeError("LineAnalyzerEngine.analyzeLines expects a DOM Element.");
    }

    const units = collectUnits(root);
    const buckets = [];

    for (const unit of units) {
      let bucket = buckets.find(item => item.key === unit.lineKey);
      if (!bucket) {
        bucket = { key: unit.lineKey, units: [] };
        buckets.push(bucket);
      }
      bucket.units.push(unit);
    }
    buckets.sort((a, b) => a.key - b.key);

    const lines = [];
    const words = [];

    buckets.forEach((bucket, lineIndex) => {
      const lineWords = [];
      let current = [];

      const flush = () => {
        if (!current.length) return;
        const wordIndex = lineWords.length;
        const chars = current.map((unit, charIndex) => ({
          char: unit.text,
          charIndex,
          sourceStart: unit.start,
          sourceEnd: unit.end,
          node: unit.node,
          rect: unit.rect
        }));
        const word = {
          lineIndex,
          wordIndex,
          text: current.map(unit => unit.text).join(""),
          chars
        };
        lineWords.push(word);
        words.push(word);
        current = [];
      };

      for (const unit of bucket.units) {
        if (/^\s+$/u.test(unit.text)) flush();
        else current.push(unit);
      }
      flush();

      const rects = bucket.units.map(unit => unit.rect);
      const left = Math.min(...rects.map(rect => rect.left));
      const right = Math.max(...rects.map(rect => rect.right));
      const text = bucket.units.map(unit => unit.text).join("");

      lines.push({
        lineIndex,
        text,
        width: right - left,
        wordIndexes: lineWords.map(word => word.wordIndex),
        words: lineWords
      });
    });

    return {
      targetWidth: root.clientWidth,
      words,
      lines
    };
  }

  window.LineAnalyzerEngine = { analyzeLines };
})();
