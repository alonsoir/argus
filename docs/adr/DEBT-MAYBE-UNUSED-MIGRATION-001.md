# DEBT-MAYBE-UNUSED-MIGRATION-001 — Migrar /*param*/ a [[maybe_unused]]

**Estado:** BACKLOG
**Prioridad:** P3 — cosmético, post deudas P0
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

DAY 140 se usó `/*param*/` para silenciar 30+ warnings en stubs e interfaces
virtuales. El Consejo (7/8) establece que `[[maybe_unused]]` es el estándar
C++20 correcto para este caso.

## Política aprobada (Consejo DAY 140, 7/8)

- **Interfaces virtuales y stubs:** `[[maybe_unused]]` en la declaración
- **Stubs temporales de implementación:** `/*param*/` aceptable
- **Variables locales no usadas:** `[[maybe_unused]]`

## Ejemplo

```cpp
// Antes (DAY 140):
double IndexHealthMonitor::compute_cv(const void* /*index*/) { ... }

// Después (post-migración):
double IndexHealthMonitor::compute_cv([[maybe_unused]] const void* index) { ... }
```

## Test de cierre

`grep -r "/\*.*\*/" src/ include/ | grep -v "copyright\|TODO\|NOTE"` devuelve
solo instancias justificadas con comentario explícito.

## Referencias

- Consejo DAY 140 (7/8 — Claude disiente para interfaces virtuales)
- ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen: `[[maybe_unused]]` correcto
