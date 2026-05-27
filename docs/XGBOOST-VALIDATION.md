# XGBoost Plugin — Validation Checklist & Merge Gate

**ADR**: ADR-026 D2 — Track 1 (nodo único)  
**Feature**: `feature/adr026-xgboost`  
**Dataset de validación**: CTU-13 Neris  
**Baseline**: Random Forest embebido — F1=0.9985, Precision=0.9969, Recall=1.0000, latencia 0.24–1.06 μs  
**Apertura**: DAY 118 — 15 Abril 2026

---

## Criterio de merge a main

**No hay merge sin todos los gates en verde.**

| Gate | Umbral | Baseline RF | Estado |
|------|--------|-------------|--------|
| F1-score (CTU-13 Neris) | ≥ 0.9985 | 0.9985 | ⏳ |
| Precision | ≥ 0.99 | 0.9969 | ⏳ |
| Recall | ≥ 0.99 | 1.0000 | ⏳ |
| FPR | ≤ 0.001 | 0.0066 | ⏳ |
| Latencia por inferencia | ≤ 2× baseline RF | 0.24–1.06 μs | ⏳ |
| Plugin firmado Ed25519 (ADR-025) | obligatorio | n/a | ⏳ |
| TEST-INTEG-4a..4e verde | obligatorio | PASSED | ⏳ |
| make test-all verde | obligatorio | PASSED | ⏳ |
| Revisión Consejo de Sabios | unanimidad o mayoría | n/a | ⏳ |

> **Nota gate médico (D6 ADR-026, Gemini DAY 104):** Precision ≥ 0.99 es
> inamovible para entornos hospitalarios. Un falso positivo que bloquea
> acceso a base de datos de anestesia es más catastrófico que un falso
> negativo. Este threshold no es negociable.

---

## Comparativa RF vs XGBoost — a completar

| Métrica | RF (baseline) | XGBoost (resultado) | Delta |
|---------|--------------|---------------------|-------|
| F1-score | 0.9985 | — | — |
| Precision | 0.9969 | — | — |
| Recall | 1.0000 | — | — |
| FPR | 0.0066 | — | — |
| Latencia media (μs) | ~0.65 | — | — |
| RAM (plugin cargado) | ~1.28 GB pipeline | — | — |
| Tamaño modelo (.so) | — | — | — |

> Esta tabla es contribución científica publicable en arXiv:2604.04952 §4.

---

## Checklist de implementación

### Fase 1 — Entorno y dependencias
- [ ] XGBoost C++ library disponible en VM (libxgboost.so o estática)
- [ ] CMakeLists.txt del plugin con linkado correcto
- [ ] `libplugin_xgboost.so` compila sin warnings con `-Wall -Wextra -Wpedantic`

### Fase 2 — Entrenamiento offline
- [ ] Dataset CTU-13 Neris disponible (mismo split que baseline RF)
- [ ] Script de entrenamiento Python (XGBoost sklearn API o nativo)
- [ ] Modelo exportado en formato compatible con C++ runtime (JSON o binary)
- [ ] Mismo feature set que RF baseline (documentar columnas exactas)
- [ ] Métricas de entrenamiento registradas y reproducibles

### Fase 3 — Plugin
- [ ] `libplugin_xgboost.so` implementa `invoke_all(MessageContext&)`
- [ ] Modo `PLUGIN_MODE_NORMAL` — integración en ml-detector
- [ ] Fail-closed: `std::terminate()` si modelo no carga
- [ ] Plugin firmado: `make sign-plugins` → `.sig` válido
- [ ] Verificación TOCTOU-safe (ADR-025 heredado)

### Fase 4 — Validación CTU-13 Neris
- [ ] Replay CTU-13 Neris con pipeline 6/6 RUNNING
- [ ] 4 runs mínimo (consistencia, no cherry-picking)
- [ ] F1 ≥ 0.9985 en todos los runs
- [ ] Precision ≥ 0.99 en todos los runs
- [ ] Latencia medida con el mismo harness que RF baseline
- [ ] Comparativa RF vs XGBoost documentada en tabla arriba

### Fase 5 — Integración y tests
- [ ] TEST-INTEG-4a..4e PASSED con libplugin_xgboost.so
- [ ] TEST-INTEG-SIGN PASSED
- [ ] make test-all verde
- [ ] TEST-PROVISION-1 8/8 verde
- [ ] AppArmor 6/6 enforce — 0 denials con XGBoost cargado

### Fase 6 — Revisión Consejo de Sabios
- [ ] Prompt de revisión con métricas completas
- [ ] Consejo: unanimidad o mayoría (≥4/7) para merge
- [ ] Veredicto documentado en `docs/consejo/CONSEJO-DAY-XYZ-adr026.md`

### Fase 7 — Documentación y merge
- [ ] ADR-026 actualizado: D2 Track 1 → IMPLEMENTADO
- [ ] arXiv:2604.04952 §4 actualizado con tabla RF vs XGBoost
- [ ] CHANGELOG-v0.5.0.md creado
- [ ] `git merge --no-ff feature/adr026-xgboost`
- [ ] Tag `v0.5.0-xgboost-plugin`

---

## Prerequisitos documentados

### Esta feature (nodo único)
- ✅ ADR-025 Ed25519 — plugin integrity (MERGEADO main DAY 114)
- ✅ AppArmor 6/6 enforce (DAY 118)
- ✅ make test-all CI gate (DAY 118)

### Segundo nodo (NO bloquea esta feature)
- ⏳ DEBT-PROTO-002 — schema versionado CSV (ADR-026 D9)
  *Bloquea coordinación multi-nodo, no desarrollo del plugin en nodo único.*

### Producción hospitalaria real (NO bloquea esta feature)
- ⏳ DPIA formal (LOPD/GDPR Art. 9 — ADR-026 D7)
- ⏳ Acuerdo legal con cada institución
- ⏳ Anonimización irreversible en nodo antes de envío

---

## Scope explícito — qué NO entra en esta feature

| Ítem | ADR destino |
|------|-------------|
| Distribución BitTorrent de plugins (D4) | ADR-026 Track 2 |
| Telemetría nodo→servidor HTTPS:443 (D5) | ADR-028 |
| Federated Learning (D3) | POSPUESTO indefinidamente |
| Modelo vLLM servidor central (D10) | ADR-026 Track 2, Year 2-3 |
| Rollback remoto firmado (D8) | ADR-028 |
| DEBT-PROTO-002 (D9) | feature/proto-002 |
| Segundo nodo activo | post DEBT-PROTO-002 |

---

*aRGus NDR — "un escudo, nunca una espada"*  
*Via Appia Quality · piano piano · pasito a pasito*