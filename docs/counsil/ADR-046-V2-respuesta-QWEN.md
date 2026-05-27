# 🏛️ Consejo de Sabios — Respuestas a ADR-046 (DAY 158)

*Via Appia Quality — construido para permanecer.*

Alonso, recibimos el ADR-046 v2. La maduración sobre el rol de Wazuh se refleja con claridad en la arquitectura: **cuatro planos ortogonales, disparadores múltiples, correlación event-driven**. Es una evolución sólida.

A continuación, las respuestas a las seis preguntas abiertas, con el rigor que exige una plataforma de seguridad crítica.

---

## 1. Timeout de espera (60s) — ¿Configurable por disparador?

**Recomendación:** Sí, configurable por tipo de disparador, con valores por defecto documentados.

```yaml
correlation:
  timeout:
    default: 60s
    by_trigger:
      argus: 30s      # detección en tiempo real, baja latencia
      suricata: 30s   # alertas casi instantáneas
      zeek: 45s       # logs de protocolo con ligero buffering
      wazuh: 90s      # canal asíncrono OSSEC, posible latencia de agente
```

**Justificación:**
- La asincronía de Wazuh es arquitectural, no un defecto. Forzarlo a 60s podría descartar señal válida.
- Suricata y aRGus operan en tiempo real de red; esperar 90s por ellos degradaría la respuesta.
- El `correlation-engine` debe registrar métricas de `time_to_convergence` por nodo para ajustar estos valores empíricamente en producción.

**Riesgo mitigado:** Si un disparador no responde dentro de su timeout, el registro enriquecido se genera con `null` para esa fuente — mejor un registro incompleto que una ventana de crisis perdida.

---

## 2. Orden de integración en Vagrantfile — ¿Suricata o Zeek primero?

**Recomendación: Suricata primero.**

**Razonamiento estratégico:**
| Criterio | Suricata | Zeek |
|----------|----------|------|
| Valor inmediato | ✅ Etiquetado automático (ground truth) | ❌ Contexto semántico (valioso, pero secundario) |
| Complejidad de integración | Baja (eve.json estructurado) | Media (múltiples logs, formatos heterogéneos) |
| Dependencia para validación | ✅ Permite empezar a medir F1 enriquecido | ❌ Requiere parsing adicional para features |
| Impacto en paper v24 | ✅ Datos etiquetados para curva F1 | ⚠️ Complementario, no esencial para hipótesis principal |

**Plan sugerido:**
1. Integrar Suricata → validar que el etiquetado automático funciona en Vagrant.
2. Medir impacto en recursos (DEBT-ARGUSPP-RESOURCE-001).
3. Integrar Zeek → enriquecer el grafo Neo4j con nodos `Domain`, `Certificate`.
4. Validar que la correlación Suricata+Zeek mejora la detección sobre aRGus solo.

---

## 3. Wazuh en el edge — ¿P1 o P2?

**Recomendación: P1, pero con modalidad "light" en Tier 1.**

**Justificación:**
- Wazuh es el único que ve el plano de host. Sin él, la hipótesis de "cuatro planos ortogonales" queda incomprobada.
- Sin embargo, en hardware mínimo (RPi5), ejecutar Wazuh agent + aRGus + Suricata podría saturar CPU.

**Propuesta de implementación escalonada:**
```
Tier 1 (RPi5):
  └── Wazuh agent en modo "minimal": solo FIM crítico + auth events
      (configurable via wazuh.conf, desactivar módulos no esenciales)

Tier 2+ (N100 o superior):
  └── Wazuh agent completo + syscalls + procesos
```

**Condición de aceptación:** El `correlation-engine` debe funcionar correctamente aunque Wazuh envíe registros vacíos — la ausencia de señal de host es, en sí misma, información.

---

## 4. `correlation-engine` v1 scope mínimo — ¿Acuerdo con la propuesta?

**Recomendación: Acuerdo condicionado.**

✅ **Aprobado para v1:**
- Disparador único: aRGus (el más maduro, menor riesgo)
- Buffer circular por nodo + flush a Parquet enriquecido
- Timeout configurable + registro de métricas de convergencia
- Esqueleto de estructura `CrisisWindow` (preparado para 4 fuentes)

⚠️ **Condiciones para v1:**
1. La interfaz interna debe permitir añadir Suricata/Zeek/Wazuh como disparadores sin refactorización mayor.
2. El esquema Parquet debe incluir campos opcionales para las 4 fuentes desde el día 1 (evitar migración costosa después).
3. Documentar explícitamente que v1 no hace join semántico — solo agrupación temporal por nodo.

**v2 (con hardware físico):** Join multi-fuente completo + grafo Neo4j en tiempo real + meta-learner.

---

## 5. `mitre-generator` — ¿ADR propio o sección en ADR-046?

**Recomendación: ADR-047 independiente.**

**Razones:**
- `mitre-generator` es un componente con ciclo de vida propio: orquestación de ataques, generación de manifiestos, integración con Atomic Red Team/Caldera.
- Tiene dependencias externas complejas (PowerShell, Python, APIs de MITRE).
- Su validación requiere un proceso de pentesting separado del pipeline de correlación.
- Un ADR propio permite revisar su diseño de seguridad (¿cómo se autentican los scripts de ataque? ¿cómo se protege el manifiesto?).

**Relación con ADR-046:** ADR-047 debe declarar explícitamente que es prerequisito para la validación empírica de ADR-046, pero no para su implementación inicial.

---

## 6. Experimento académico vs sintético — ¿Datos recuperables para paper v24?

**Recomendación: Auditoría inmediata de artefactos + plan de regeneración si es necesario.**

**Acciones propuestas:**
1. **Buscar en almacenamiento episódico** (ADR-043): ¿Existen registros de las curvas F1 vs ratio académico/sintético en Neo4j o Parquet?
2. **Revisar notebooks de experimentación**: ¿Quedó código en `experiments/` que permita regenerar las curvas?
3. **Si no hay datos recuperables**: Ejecutar un experimento mínimo con 3 puntos (0%, 50%, 100% sintético) usando los datasets ya disponibles (CTU-13, CIC-IDS-2017, sintéticos actuales).

**Nota crítica para el paper:** Si los datos originales no son recuperables, ser transparentes: *"Los experimentos iniciales sugirieron que 100% sintético supera a mezclas; esta hipótesis se valida formalmente en la Sección X con nuevos experimentos reproducibles"*. La honestidad metodológica refuerza, no debilita, la contribución.

---

## 🎯 Dictamen final del Consejo

**ADR-046 v2: APROBADO CON CONDICIONES**

| Condición | Prioridad | Responsable |
|-----------|-----------|-------------|
| Configurar timeouts por disparador en `correlation-engine` | P0 | Arquitectura |
| Integrar Suricata primero en Vagrantfile | P1 | DevOps |
| Wazuh agent en modo "minimal" para Tier 1 | P1 | Edge Team |
| Esquema Parquet con campos opcionales para 4 fuentes desde v1 | P0 | Data Engineering |
| Crear ADR-047 para `mitre-generator` | P1 | Alonso + Consejo |
| Auditoría de datos del experimento académico/sintético | P1 | Research |

**Próximo hito:** DAY 165 — Revisión de `correlation-engine` v1 en entorno Vagrant con aRGus + Suricata.

---

> *"La correlación no es sincronización forzada; es el reconocimiento de que la verdad emerge cuando múltiples observadores coinciden en la crisis."*

Quedamos a la espera de los avances. El camino es claro.

🏛️ **Consejo de Sabios — aRGus Project**  
*Via Appia Quality — construido para permanecer.*