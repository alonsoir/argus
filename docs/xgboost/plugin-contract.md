# aRGus NDR — XGBoost Plugin Contract (ADR-026)

## Contrato ctx->payload para plugin_process_message

Fuente: `plugin_api.h` → `MessageContext`, decisión Opción B (Consejo DAY 119):
ml-detector pre-procesa y construye el payload antes de invocar el plugin.

## Formato del payload

    ctx->payload      = float32[] contiguo, row-major
    ctx->payload_size = num_features * sizeof(float) = 23 * 4 = 92 bytes

## Invariantes (fail-closed si se violan)

| Condición                             | Acción             |
|---------------------------------------|--------------------|
| payload == nullptr                    | std::terminate()   |
| payload_size % sizeof(float) != 0    | std::terminate()   |
| payload_size / sizeof(float) != 23   | std::terminate()   |
| cualquier elemento NaN o Inf         | std::terminate()   |

## Campo schema_version

`ctx->mode` transporta la versión del esquema de features:
- `PLUGIN_MODE_NORMAL` (0) = schema v1 (23 features LEVEL1)
- Versiones futuras → nuevos valores de mode

## Flujo de invocación

    ml-detector::zmq_handler
        → FeatureExtractor::extract_level1_features(event)  // 23 floats
        → FeatureExtractor::validate_features(features)     // no NaN/Inf
        → MessageContext ctx { payload, payload_size=92, mode=NORMAL }
        → plugin_loader::invoke_all(ctx)
            → plugin_xgboost::plugin_process_message(ctx)
                → XGBoosterPredict(booster_, dmatrix, ...)
                → resultado en ctx->result ∈ [0.0, 1.0]

## Salida del plugin

- `ctx->result` ∈ [0.0, 1.0] — probabilidad de tráfico malicioso
- NaN → fallo de inferencia → Graceful Degradation D1 (ADR-023)
- Threshold de decisión: 0.5 (configurable en producción)

## Versión del esquema

Schema v1 — DAY 120 — feature set LEVEL1 (23 features)
Documentado en: docs/xgboost/features.md
