(function () {
  "use strict";
  // Rule-Pack-specific settings, not part of generic Core.
  window.BaseNormalConfig = {
    eligibility: { minConnectedGlyphs: 3 },
    boundaries: {
      // A listed non-joining glyph terminates a candidate segment and is included in it.
      members: ["ا", "أ", "إ", "آ", "د", "ذ", "ر", "ز", "و", "\u200C"],
      separators: [" ", "\t", "\n"]
    },
    selection: { fromEnd: 3 },
    rendering: {
      // Temporary compatibility values for the existing font/renderer.
      axisName: "LEXP",
      value: 500
    }
  };
})();
