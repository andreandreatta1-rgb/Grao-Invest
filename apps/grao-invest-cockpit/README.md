# Grão Invest Dashboard

Standalone React/PWA candidate for the Grão Invest scientific dashboard, powered by the internal Halley engine.

## Run

```powershell
cd apps/grao-invest-cockpit
npm install
npm run dev
```

## Test

```powershell
npm test
npm run build
```

## UX Validation

- The first screen shows Teses testadas, Validação histórica, Expectância líquida, Teses em go-live and Aprendizados aplicados.
- B3, Cripto and Imóveis appear as separate fronts.
- Clicking a thesis opens details and clicking again closes details.
- Accented words render correctly: Ações, Operações, Imóveis, Hipótese, Evidência, Validação, Refutação.
- No text sounds like investment recommendation.
- No Tailwind classes or CSS files are used for visual styling.
