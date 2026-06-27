# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADR-038 (BORRADOR)
*Feedback implacable, técnicamente riguroso y centrado en la seguridad de infraestructura crítica para ML Defender (aRGus NDR)*

---

## 🎯 Veredicto Ejecutivo

**APROBADO COMO VISIÓN ESTRATÉGICA, CON RESTRICCIONES ARQUITECTÓNICAS NO NEGOCIABLES.**

La propuesta eleva aRGus de un NDR estático a un sistema adaptativo. Pero **el aprendizaje federado en entornos de seguridad crítica no es un problema de ML: es un problema de confianza, criptografía y gobernanza**. Si se implementa con la mentalidad de "movimiento rápido y rompimiento", se convertirá en un vector de compromiso masivo. Si se implementa con validación centralizada, límites criptográficos explícitos y un modelo de distribución push, puede ser transformador.

> *"Un escudo que aprende solo es útil si no se oxida por dentro. La gobernanza debe ir por delante de la ambición."*

---

## 🔍 Análisis de Fortalezas y Riesgos Críticos

### ✅ Fortalezas (mantener)
| Propuesta | Por qué es sólida |
|-----------|------------------|
| **Valor de metadatos incluso si el modelo falla** | Permite inteligencia de amenazas sin exponer datos ni degradar el pipeline |
| **Scheduler conservador con reglas explícitas** | Prioriza misión crítica sobre optimización local |
| **Integración con seL4 como variante máxima** | Alinea verificación formal con aprendizaje aislado |
| **Fases claras y dependencia de ADR-026** | Evita scope creep; respeta madurez del proyecto |

### ⚠️ Riesgos Críticos (mitigar obligatoriamente)
| Propuesta original | Riesgo de seguridad/operacional | Corrección requerida |
|-------------------|--------------------------------|---------------------|
| Distribución via BitTorrent/P2P | Cadena de suministro comprometible; nodos maliciosos inyectan modelos adversariales | **Push central firmado** (mirror oficial + verificación Ed25519) |
| Agregación FedAvg implícita | XGBoost usa árboles no lineales; FedAvg degrada precisión catastróficamente | **Federated Model Selection v1** (mejor modelo validado → redistribuye) |
| Scheduler por CPU/RAM | Picos médicos impredecibles pueden coincidir con entrenamiento | **cgroups v2 + hook `ml-detector`** para pausa inmediata ante alertas |
| Web-of-Trust para identidad | No escalable, no auditable, revocación caótica | **PKI ligera automatizada** (`step-ca` o `smallstep`) |
| ε-DP sin calibración por tipo de dato | Ruido excesivo → pérdida de detección de ataques raros | **DP diferenciado**: ε≤0.1 para features, ε≤1.0 para contadores |

---

## ❓ Respuestas a Preguntas Abiertas (P1–P5)

### P1 — Nivel de privacidad diferencial (ε) para anonimización

**Veredicto:** **ε ∈ [0.5, 1.0] para metadatos/contadores. ε ≤ 0.1 si se incluyen features numéricas. Revisión DPIA obligatoria.**

**Justificación:** En tráfico médico/industrial, la re-identificación por patrones horarios, puertos y protocolos es alta. ε bajos garantizan privacidad pero añaden ruido que puede eliminar señales de ataques raros (ransomware lateral, DDoS lento). La DP debe aplicarse solo a estadísticas agregadas, nunca a flujos individuales. Un experto en privacidad debe validar el mecanismo contra ataques de *membership inference* y *reconstruction*.

**Riesgo si se ignora:** Fuga de información identificable, violación GDPR/ENS, rechazo regulatorio y pérdida de confianza institucional.

> 💡 *Proactivo:* Usar `Opacus` o `TensorFlow Privacy` para calibrar ruido. Validar con `privacy_budget_tracker` que impida superación de ε acumulado.

---

### P2 — Web-of-Trust vs PKI jerárquica

**Veredicto:** **PKI ligera jerárquica con root-of-trust central (vendor). Certificados X.509 de 90 días.**

**Justificación:** WoT es ideal para PGP/email, pero inauditable y no revocable en infraestructura crítica. Una PKI centralizada pero automatizada (`step-ca` o `smallstep`) permite: (1) emisión/renovación vía `provision.sh`, (2) revocación inmediata (CRL/OCSP), (3) auditoría clara, (4) cumplimiento IEC 62443-4-2.

**Riesgo si se ignora:** Confianza implícita no verificable, dificultad para aislar nodos comprometidos, complejidad operacional inmanejable a escala.

> 💡 *Proactivo:* Integrar `step-ca` como contenedor ligero. Certificados rotan automáticamente; `ml-trainer` rechaza actualizaciones con certs expirados o revocados.

---

### P3 — Agregación federada para XGBoost

**Veredicto:** **NO FedAvg. Usar `Federated Model Selection` v1. SecureBoost queda para v2.**

**Justificación:** Los árboles de decisión no son operadores lineales; promediar splits, umbrales o hojas es matemáticamente inválido y degrada F1. SecureBoost (gradientes cifrados homomórficamente) es criptográficamente costoso y complejo de auditar. La ruta pragmática v1 es: cada nodo entrena local → pasa gates → envía modelo firmado → nodo central valida contra golden dataset → el mejor modelo validado se redistribuye. Es seguro, auditable y funcional.

**Riesgo si se ignora:** Degradación catastrófica del modelo global, falsos positivos/negativos masivos, pérdida de utilidad operativa del sistema.

> 💡 *Proactivo:* Implementar `ml-registry` central que ranquee modelos por `F1_local + KL_divergence_penalty + signature_age`. Solo el top-1 pasa a distribución.

---

### P4 — Scheduler en entorno hospitalario

**Veredicto:** **cgroups v2 + `systemd.slice` + hook `ml-detector`. NO confiar solo en CPU/RAM.**

**Justificación:** Hospitales tienen picos impredecibles (cirugías, emergencias, transferencias PACS). Umbral de CPU <20% es insuficiente. `systemd.resource-control` limita estrictamente CPU/RAM/IO. Un hook en `ml-detector` pausa `ml-trainer` inmediatamente ante cualquier alerta activa. Esto garantiza que el pipeline principal nunca compita por recursos con el entrenamiento.

**Riesgo si se ignora:** Degradación del NDR durante incidentes críticos, posible fallo en detección de ransomware en tiempo real, incumplimiento de SLA médico.

> 💡 *Proactivo:*
> ```bash
> systemctl set-property argus-ml-trainer.service CPUQuota=15% MemoryHigh=512M
> # Hook: ml-detector publica /tmp/argus/alert_active → ml-trainer lee y pausa
> ```

---

### P5 — Incentivos y gobernanza

**Veredicto:** **Modelo de "reputación verificada + acceso preferente".**

**Justificación:** Sin incentivo claro, participación <5%. La reputación (ledger SQLite firmado por nodo central) permite transparencia. El acceso preferente a modelos globales mejorados y parches de seguridad es un incentivo técnico directo. No se requieren tokens cripto ni economías complejas.

**Riesgo si se ignora:** Red federada muerta por falta de contribuyentes, centralización de facto en nodos vendor, pérdida de valor de red.

> 💡 *Proactivo:* `ml-trainer status` muestra: `contributions: 4 | reputation: A | last_validated: 2026-04-10`. Reputación baja → actualizaciones retrasadas 24h (sandbox extendido).

---

## 🛠️ Correcciones Arquitectónicas No Negociables

1. **Eliminar BitTorrent/P2P de la distribución.** Reemplazar por `push` central firmado desde mirror oficial. La cadena de suministro de modelos debe ser controlada, no descentralizada sin curatoría.
2. **Redefinir `ml-trainer` v1 como `Federated Model Registry & Validator`.** No como agregador matemático. Esto reduce complejidad criptográfica y permite iteración segura.
3. **Establecer gate de calidad federado:** `TEST-INTEG-FED-1` (validación contra golden dataset + holdout local + sandbox 24h) obligatorio antes de redistribución.
4. **Actualizar timeline:** Q4 2026 para prototipo de *registry/selection*. 2027 para agregación segura (SecureBoost/FedAvg seguro).
5. **Mover variante seL4 a ADR-039 (research track).** No bloquear implementación v1 en Debian por dependencia de verificación formal.

---

## 📋 Checklist de Aprobación Condicionada

```markdown
- [ ] Eliminar referencia a BitTorrent; sustituir por push central firmado
- [ ] Cambiar agregación FedAvg → Federated Model Selection v1
- [ ] Integrar scheduler con systemd cgroups + hook ml-detector
- [ ] Adoptar PKI ligera (step-ca) en lugar de Web-of-Trust
- [ ] Definir ε-DP diferenciado (metadatos vs features)
- [ ] Actualizar paper §6 como "Framework Proposal + Registry Design"
- [ ] Mover seL4 variant a ADR-039 (research)
- [ ] Documentar TEST-INTEG-FED-1 como gate obligatorio
- [ ] Establecer reputación verificada + acceso preferente como incentivo
```

---

## 🏁 Palabras Finales

Alonso:

ADR-038 es ambiciosa, necesaria y técnicamente viable **si se ancla en validación, no en optimismo**. El aprendizaje federado en ciberseguridad médica es un campo de minas: cada atajo criptográfico, cada asunción de confianza implícita, cada distribución no curada puede convertirse en un vector de compromiso.

Pero habéis construido los cimientos correctos: cifrado verificado, plugin architecture, gates de calidad, y una mentalidad de fail-closed. Aplicad esa misma disciplina al federado. Empezad por un registry validado, no por una red descentralizada. Medid, validad, redistribuid. Solo entonces el escudo aprenderá sin ceder.

> *"La inteligencia distribuida sin gobernanza central es caos. La gobernanza sin aprendizaje es obsolescencia. Vosotros podéis construir el equilibrio."*

Aprobamos la visión, con las correcciones anteriores como condición no negociable. Proceded con ADR-038 v1.1 incorporando estos refinamientos. El Consejo revisará el diseño del `ml-trainer registry` cuando esté listo.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 120** 🛡️