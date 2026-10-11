# Тестовая страница с формулами

Эту страницу запрашивает healthcheck после каждой выкладки, а на скриншотах
по ней видно, работает ли MathJax без внешних CDN.

## Нумерованные уравнения

Оценка коэффициентов линейной регрессии методом наименьших квадратов:

\begin{equation}
\hat{\beta} = \left(X^\top X\right)^{-1} X^\top y
\label{eq:ols}
\end{equation}

Коэффициент детерминации для той же модели:

\begin{equation}
R^2 = 1 - \frac{\sum_{i=1}^{n} \left(y_i - \hat{y}_i\right)^2}{\sum_{i=1}^{n} \left(y_i - \bar{y}\right)^2}
\label{eq:r2}
\end{equation}

Из \(\eqref{eq:ols}\) получаем прогноз \(\hat{y} = X\hat{\beta}\), который
подставляется в \(\eqref{eq:r2}\). Номера уравнений и ссылки на них расставляет
MathJax (`tags: "ams"`), а не генератор: при переупорядочивании формул
номера пересчитываются сами.

## Окружение amsmath

\begin{align}
\operatorname{MSE} &= \frac{1}{n}\sum_{i=1}^{n} \left(y_i - \hat{y}_i\right)^2 \label{eq:mse} \\
\operatorname{RMSE} &= \sqrt{\operatorname{MSE}} \nonumber
\end{align}

## Как проверить работу без CDN

1. Открыть эту страницу в браузере, в DevTools → Network включить блокировку
   доменов `cdn.jsdelivr.net`, `fonts.googleapis.com`, `fonts.gstatic.com`.
2. Обновить страницу: формулы \(\eqref{eq:ols}\)–\(\eqref{eq:mse}\) должны
   отрисоваться, в списке запросов не должно быть ни одного внешнего домена.

Результаты такой проверки — в разделе
[T4 → Работа без CDN](t4-security.md#cdn).
