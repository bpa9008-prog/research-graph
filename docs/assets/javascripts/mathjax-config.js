// Конфигурация MathJax 3 для pymdownx.arithmatex (generic: true).
// Скрипт подключается до tex-svg.js, поэтому объект window.MathJax
// успевает стать конфигурацией, а не перезаписаться библиотекой.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    tags: "ams", // нумерация уравнений и \eqref, как в LaTeX
  },
  svg: {
    fontCache: "global", // SVG-вывод не тянет веб-шрифты с CDN
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
};

// Material переписывает содержимое страниц без перезагрузки (instant loading
// здесь выключен, но document$ есть всегда) — перерисовываем формулы.
if (typeof document$ !== "undefined") {
  document$.subscribe(() => {
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.startup.output.clearCache();
      MathJax.typesetClear();
      MathJax.texReset();
      MathJax.typesetPromise();
    }
  });
}
