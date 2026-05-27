# PRE-ADR-026 — Arquitectura P2P para Distribución de Modelos y Aprendizaje Federado en Flota

**Estado**: BORRADOR v2 — Para discusión en Consejo de Sabios (DAY 104)  
**Autor**: Alonso Isidoro Román (aironman)  
**Fecha**: 2026-04-04  
**Prerequisitos**: ADR-025 (Plugin Integrity via Ed25519), ADR-021 (deployment.yml SSOT)  
**Horizon**: Medio-largo plazo (~Año 1–3 post-estabilización del plugin system)

---

## 1. Contexto y motivación

El pipeline de ML Defender (aRGus NDR) produce CSVs de flows de red diariamente en cada nodo desplegado. A medida que la flota crezca (hospitales, escuelas, municipios), se acumularán TB de datos de tráfico real de infraestructura crítica — un activo científico y operacional de alto valor sin equivalente actual en la literatura de NDR para recursos limitados.

**Observación clave sobre los nodos target**: Los despliegues en hospitales, municipios y escuelas operan en hardware limitado y con personal técnico reducido. **No pueden permitirse infraestructura de entrenamiento local**. Solo pueden observar, capturar y enviar telemetría. Cualquier arquitectura que asuma capacidad de cómputo en los nodos está mal diseñada para este dominio.

**Consecuencia arquitectónica**: El modelo de aprendizaje debe ser **asimétrico por diseño**:
- Nodos: observan y envían telemetría comprimida
- Servidor central: aprende, valida y distribuye mejoras como plugins

Esta asimetría es la premisa fundamental de este PRE-ADR.

---

## 2. Clarificación de terminología: ¿qué es un "LLM" en este contexto?

Antes de presentar opciones, es necesario clarificar una ambigüedad que podría generar confusión en el Consejo.

**Los LLMs son modelos de secuencias de texto.** Los CSVs del pipeline son datos numéricos tabulares con features de grafos (src_ip, dst_ip, bytes, packets, duration, protocol flags, etc.). El gap arquitectónico es real:

| Objetivo | Arquitectura correcta | ¿LLM? |
|---|---|---|
| Detectar intrusiones en flows numéricos | Random Forest, XGBoost, FT-Transformer | No |
| Especialistas por tipo de ataque (Neris, WannaCry, etc.) | RF/XGBoost pequeños exportados a ONNX | No |
| Clasificar patrones nuevos con pocos ejemplos | TabPFN, few-shot tabular | No |
| *Explicar* en lenguaje natural por qué algo es un ataque | LLM fino-tuneado + RAG | Sí |
| Responder preguntas operacionales ("¿por qué está en cuarentena este host?") | LLM + contexto de flows (ya en roadmap: TinyLlama) | Sí |
| Razonamiento sobre campañas de ataque multi-nodo | LLM grande (vLLM server) + contexto agregado | Sí |

**Conclusión**: La detección en sí no es un problema de LLM. Los LLMs tienen valor en la **capa de explicabilidad e interfaz**, no en la capa de clasificación. Confundir ambas capas llevaría a una arquitectura sobredimensionada e ineficiente para nodos con recursos limitados.

---

## 3. Arquitectura propuesta en dos tracks

### Track 1 — RF Specialists como plugins (horizonte Año 1)

Extensión natural del sistema de plugins actual (ADR-012, ADR-025):

```
Nodos fleet:
  pcap → features CSV → telemetría comprimida+firmada → servidor central

Servidor central:
  telemetría agregada de N nodos
  → entrena RF specialist por tipo de ataque (Neris, WannaCry, SMB-scan, etc.)
  → valida: F1 > threshold_mínimo && FPR < threshold_máximo
  → si pasa validación: empaqueta como plugin ONNX firmado con Ed25519
  → distribuye a flota (BT + verificación ADR-025)
  → nodos instalan plugin sin reinicio (hot-reload)
```

**Por qué RF specialists y no un modelo monolítico**:
- Modelos pequeños → inferencia en hardware limitado (<100ms en Raspberry Pi clase)
- Interpretables: feature importance explicable a personal no técnico
- Fallo aislado: un specialist defectuoso no tumba la detección general
- Análogo comprobado: CrowdStrike y Darktrace usan internamente ensembles de especialistas

**Prerequisito técnico duro**: Schema CSV versionado explícitamente antes de cualquier entrenamiento centralizado. Un cambio de features rompe el histórico de TB acumulado. Propuesta: formalizar como DEBT-PROTO-002.

---

### Track 2 — LLM especializado en servidor vLLM (horizonte Año 2–3)

No sustituye al Track 1. Lo complementa añadiendo **explicabilidad y razonamiento**:

```
Servidor central (Track 2):
  telemetría agregada → FT-Transformer tabular (detección avanzada)
  + narrativas de ataque generadas → fine-tune LLM pequeño (Phi-3 / Mistral 7B)
  → desplegado en servidor vLLM propio

Casos de uso:
  "¿Por qué este host está en cuarentena?" → respuesta en español
  "¿Qué campaña de ataque comparten estos 3 hospitales esta semana?" → análisis agregado
  "Genera regla de firewall para este patrón" → salida estructurada para firewall-acl-agent
```

**Sobre la formación de narrativas de flows para fine-tuning**:
Los CSVs no se usan directamente para fine-tuning del LLM. Se convierten primero a texto estructurado:
```
"Host 192.168.1.5 contactó 847 destinos únicos en 2s usando puerto 445,
con ratio bytes/paquete consistente con SMB scan. Clasificado como WannaCry
por specialist RF-SMB-v2 con confianza 0.997."
```
Ese texto sí es input válido para fine-tuning de un LLM.

---

## 4. Sobre distribución P2P (el rol real de BitTorrent)

BitTorrent es óptimo para **distribución** (1→muchos), no para **agregación** (muchos→1). La telemetría de los nodos al servidor sigue siendo push/pull convencional (HTTPS, ZeroMQ o gRPC). BT entra solo en la redistribución de plugins ONNX validados:

```
Servidor publica plugin_rf_wannacry_v3.onnx.torrent + firma Ed25519
  → Nodo-A descarga + verifica firma (ADR-025)
  → Nodo-A se convierte en seeder
  → Nodo-B descarga desde Nodo-A + verifica firma independientemente
  → Servidor sirve solo el torrent inicial, la flota se autoabastece
```

**Ventaja estratégica**: En un escenario de ataque coordinado donde el servidor central está bajo DDoS, la flota puede seguir distribuyendo modelos de respuesta entre sí. Resiliencia por diseño.

---

## 5. Sobre entrenar en un portátil (pregunta de aprendizaje del autor)

**¿Es posible aprender el pipeline completo en hardware personal?**

| Tarea | Viabilidad en portátil | Tiempo estimado |
|---|---|---|
| Entrenar RF con CSVs propios | ✅ Sin problemas | Segundos-minutos |
| Exportar modelo a ONNX | ✅ Sin problemas | Trivial |
| Fine-tuning Phi-3 Mini (3.8B) con QLoRA 4-bit | ⚠️ Posible pero lento | Horas por epoch |
| Pre-training LLM desde cero | ❌ No viable | Semanas/meses |

**Recomendación de aprendizaje progresivo**:
1. Primero: entrenar un RF specialist completo con CTU-13 o datos propios → exportar ONNX → validar F1 → empaquetar como plugin. Ver el ciclo completo.
2. Segundo: experimentar con FT-Transformer en Google Colab (GPU gratuita).
3. Tercero: fine-tuning con QLoRA en Colab o instancia cloud small. No en portátil.

El valor del portátil es entender el **ciclo completo de vida de un modelo**, no la escala.

---

## 6. Preguntas abiertas para el Consejo

1. **Track 1 prerequisito**: ¿Debe formalizarse el versionado del schema CSV (DEBT-PROTO-002) antes de cualquier trabajo de agregación de telemetría? ¿Es un bloqueante duro?

2. **Protocolo de telemetría nodo→servidor**: ¿ZeroMQ (ya en stack), gRPC, o HTTPS simple? ¿Qué overhead es aceptable en nodos limitados?

3. **Threshold de validación de plugins**: ¿Qué criterios exactos debe pasar un RF specialist para ser distribuido a la flota? ¿F1 > 0.99? ¿Evaluado sobre qué dataset de referencia?

4. **Privacidad de telemetría**: Antes del Track 2, ¿es suficiente anonimizar IPs (hash salado) o se necesita análisis legal formal bajo LOPD para datos de hospitales españoles?

5. **FT-Transformer vs XGBoost**: Para el Track 2 tabular, ¿justifica FT-Transformer la complejidad adicional sobre XGBoost para este dominio? El Consejo debe pronunciarse con evidencia de benchmarks en datos de red.

6. **vLLM server**: ¿Qué modelo base es más adecuado para fine-tuning en explicabilidad de seguridad de red — Phi-3 Mini, Mistral 7B, o Llama 3.1 8B? Criterios: licencia open-source compatible, huella de memoria, rendimiento en razonamiento estructurado.

7. **Ciclo de vida de plugins**: ¿Cómo se retira un specialist que degrada con drift de datos? ¿Hay un mecanismo de rollback en la flota?

---

## 7. Decisiones que NO se toman aquí

- Esta PRE-ADR no modifica la arquitectura actual del pipeline.
- No define implementación del servidor central de agregación.
- No compromete ningún trabajo hasta alcanzar ~5 nodos activos en producción.
- El trabajo inmediato sigue siendo: ADR-025 implementación + TEST-INTEG-SIGN-1 a 7.

---

## 8. Contexto académico relevante

- **FedAvg** (McMahan et al., 2017) — referencia fundacional de aprendizaje federado.
- **Flower / flwr** (Beutel et al., 2022) — framework FL open-source candidato.
- **FT-Transformer** (Gorishniy et al., 2021) — Transformers para datos tabulares, benchmark tabular SOTA.
- **TabPFN** (Hollmann et al., 2022) — few-shot para tabular sin entrenamiento explícito.
- **CTU-13** (Garcia et al., 2014) — precedente directo: dataset propietario como activo académico.
- **Gradient Inversion Attacks** (Geiping et al., 2020) — amenaza de privacidad relevante si se adopta FL puro.
- **QLoRA** (Dettmers et al., 2023) — fine-tuning eficiente en hardware limitado.

---

## 9. Posición preliminar del autor

La visión a largo plazo es correcta y coherente: nodos ligeros que observan y envían, servidor central que aprende y distribuye mejoras validadas como plugins. Los LLMs tienen su lugar pero en la capa de explicabilidad, no en la detección. BitTorrent es elegante para la redistribución de plugins pero no para la telemetría.

**Recomendación al Consejo**: Validar la asimetría nodo/servidor como principio arquitectónico. Pronunciarse sobre el protocolo de telemetría y los thresholds de validación de plugins, que son las decisiones técnicas más cercanas e impactantes.

---

*Preparado para sesión del Consejo de Sabios — DAY 104*  
*Prompt al Consejo: evaluar cada pregunta abierta con criterios de (1) complejidad de implementación, (2) cumplimiento LOPD para datos hospitalarios, (3) viabilidad en hardware limitado de nodos, (4) valor científico/académico.*