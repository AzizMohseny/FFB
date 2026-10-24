(function () {
  "use strict";

  let timer = null;
  let observedEditor = null;
  let callback = null;
  let resizeObserver = null;

  function start(editor, runCallback) {
    observedEditor = editor;
    callback = runCallback;

    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (typeof callback === "function") callback();
      }, (window.JustyConfig && window.JustyConfig.debounceMs) || 180);
    };

    if (resizeObserver) resizeObserver.disconnect();
    if (observedEditor && "ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(schedule);
      resizeObserver.observe(observedEditor);
    }

    window.addEventListener("resize", schedule);
  }

  window.JustyRuntime = { start };
})();