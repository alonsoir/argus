Como **Consejo de Sabios**, hemos analizado vuestro informe del DAY 161 y las cinco preguntas planteadas. A continuación, nuestro veredicto colegiado sobre cada una de ellas.

---

### Q1 — Wire Protocol Test: ¿Segundo test con CryptoTransport completo?

**Veredicto del Consejo: El test actual de protocolo binario + los tests existentes de `crypto-transport` son suficientes. No es necesario un segundo test integrado en este momento.**

**Razonamiento:** El principio de responsabilidad única en testing es claro: `test_wire_protocol.cpp` valida la capa de serialización binaria (LZ4 LE uint32_t), mientras que los tests de `crypto-transport` validan la capa de cifrado (ChaCha20-Poly1305) y compresión. La combinación de ambas capas ya está cubierta indirectamente por:

1. Los tests unitarios de `crypto-transport` que ejercitan el pipeline completo de cifrado+compresión sobre datos reales.
2. Los tests de integración del sniffer (`test-e2e-live`) que transitan por el camino completo: captura → compresión → cifrado → transmisión.

El bug DEBT-FIREWALL-CRYPTO-FORMAT-001 de DAY 98 fue precisamente un fallo de formato binario en la capa de serialización —no de cifrado— y el test actual ya lo habría detectado. Añadir un test que pase por `CryptoTransport` completo duplicaría cobertura sin añadir valor de detección de regresiones que no esté ya cubierto.

**Recomendación:** Si en el futuro se detecta un bug que escape a esta combinación de tests, entonces sí se justificaría un test integrado adicional. Por ahora, mantenemos el principio de mínima duplicación.

---

### Q2 — Jenkinsfile.dev vs Jenkinsfile.prod: `agent any` vs `agent { label 'argus-server' }`

**Veredicto del Consejo: El diseño actual es correcto para la fase actual (Mac del fundador + VM Vagrant). La migración a `agent { label 'argus-server' }` debe ocurrir cuando Jenkins se despliegue en el servidor FEDER con hardware físico dedicado.**

**Razonamiento:** La separación `Jenkinsfile.dev` / `Jenkinsfile.prod` es una decisión arquitectónica sólida que reconoce dos realidades operativas distintas:

| Aspecto | `Jenkinsfile.dev` | `Jenkinsfile.prod` |
|---|---|---|
| Entorno | Mac fundador + Vagrant | Servidor FEDER físico |
| Agente | `agent any` (Jenkins y Vagrant co-residen) | `agent { label 'argus-server' }` |
| Stages | Wire Protocol, Unit Tests, Enterprise Plugin | Pipeline completo + gate ODR |
| Credenciales | No requiere Vault token real | Requiere `vault-enterprise-token` |

El uso de `agent any` en dev es pragmático: Jenkins corre en la misma máquina que Vagrant, por lo que no hay separación física que justifique un label específico. La transición a `agent { label 'argus-server' }` debe ocurrir cuando:

1. Jenkins se despliegue en el servidor FEDER (hardware físico UEx).
2. Exista al menos un nodo adicional (RPi5 o N100) que actúe como agente separado.
3. La pipeline Jinja2 esté operativa y se requiera generar configuraciones por perfil hardware.

**Recomendación:** Mantener el diseño actual. Documentar en el `Jenkinsfile.dev` un comentario `TODO: migrar a agent { label 'argus-server' } cuando Jenkins esté en FEDER`.

---

### Q3 — DEBT-CONFIG-JINJA2-PIPELINE-001: ¿Valores calculados en runtime o fijos por perfil?

**Veredicto del Consejo: Valores fijos por perfil (`naive`/`edge-low`/`edge-medium`/`edge-high`). No calcular en runtime. El cálculo automático se reserva para una fase futura (post-FEDER) con validación rigurosa.**

**Razonamiento:** El principio rector del proyecto es la determinación y reproducibilidad. Calcular valores óptimos en runtime introduce:

1. **No determinismo**: Dos ejecuciones consecutivas en el mismo hardware podrían producir configuraciones diferentes si las condiciones de carga varían (otros procesos, temperatura del SoC, etc.).
2. **Imposibilidad de auditoría**: Los datasets de valor científico para UEx/INCIBE requieren configuraciones exactamente reproducibles.
3. **Riesgo de regresión silenciosa**: Un cambio en la heurística de cálculo podría degradar el rendimiento sin que ningún test lo detecte, ya que el valor "óptimo" no tiene un ground truth fijo.

El diseño acordado —JSONs originales sagrados, plantillas Jinja2, valores por perfil— es correcto. Los perfiles deben definirse con valores fijos validados empíricamente para cada hardware objetivo:

| Perfil | Hardware objetivo | Worker threads | Compresión |
|---|---|---|---|
| `naive` | Vagrant/VirtualBox (lab) | 2 | Nivel 1 |
| `edge-low` | RPi5 (4 GB) | 4 | Nivel 1 |
| `edge-medium` | N100 (8 GB) | 8 | Nivel 3 |
| `edge-high` | Servidor FEDER (16+ GB) | 16 | Nivel 1 |

El script de generación (`make generate-configs`) debe aceptar el perfil como parámetro explícito y producir los JSONs generados de forma determinista.

**Recomendación:** Añadir un test de regresión que verifique que los JSONs generados para un perfil dado son bit a bit idénticos entre ejecuciones (`diff` estricto). Esto blinda el principio de determinismo.

---

### Q4 — EMECAS++ y el fix del delta E2E: ¿Inyectar tráfico sintético?

**Veredicto del Consejo: No inyectar tráfico sintético. El test debe medir solo tráfico orgánico. Pero debe implementarse un mecanismo de fallback condicional.**

**Razonamiento:** El propósito del test `test-e2e-live` es verificar que el pipeline completo funciona en condiciones reales. Inyectar tráfico sintético:

1. **Falsea el significado del test**: Un test que inyecta su propio tráfico no detecta fallos en la captura real del sniffer (eBPF, interfaces, permisos).
2. **Oculta regresiones**: Si el sniffer rompe la captura de tráfico real, el test pasaría igualmente gracias al tráfico sintético inyectado.
3. **Rompe el principio de no interferencia**: El test no debe modificar el estado del sistema que está midiendo.

**Solución propuesta — Fallback condicional con marcador de advertencia:**

```
test-e2e-live:
  1. snapshot inicial
  2. esperar 60s
  3. snapshot final
  4. delta = final - inicial
  5. SI delta >= 1 → TEST PASSED (tráfico orgánico detectado)
  6. SI delta == 0 → ADVERTENCIA: "No se detectó tráfico orgánico en 60s.
     ¿Vagrant aislado? ¿Interfaz sin tráfico?"
     → TEST SKIPPED (no FAILED) con marcador EMECAS++ DEBT-E2E-LIVE-DELTA-002
```

Esto evita falsos negativos que bloqueen el pipeline mientras preserva la integridad del test. La advertencia es visible en el reporte de EMECAS++ pero no rompe el gate.

**Recomendación:** Implementar el fallback condicional en DAY 162 como mini-fix, antes de proceder al hito principal.

---

### Q5 — Prioridad DAY 162: Siguiente hito más valioso

**Veredicto del Consejo: Opción A — DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2: primera señal externa).**

**Razonamiento:** Evaluamos las cuatro opciones según tres criterios: valor estratégico, desbloqueo de dependencias y madurez del terreno.

| Opción | Valor estratégico | Desbloquea dependencias | Madurez del terreno |
|---|---|---|---|
| **A) Suricata F2** | **Muy alto**: Primera señal externa al sistema. Hito científico UEx/INCIBE. | Desbloquea el paper definitivo con comparativa multi-engine. | Suricata 6.0.10 ya operativo en Vagrant. 50,010 reglas ET Open cargadas. Experimentos offline completados. |
| B) NTP-001 | Alto: Prerequisito para correlación multi-engine. | Necesario para correlación temporal entre engines. | Requiere diseño de protocolo de sincronización. Sin hardware físico para validar. |
| C) CRYPTO-AUTONOMY-001 | Medio: EXTENDED_AUTONOMY state machine. | Ninguno inmediato. | State machine actual funciona. Extenderla sin casos de uso concretos es premature optimization. |
| D) ALERTING-LIBCRYPTO | Bajo-Medio: Refactor interno. | Ninguno. | AlertClient funciona. Mover a libcrypto_provider es limpieza arquitectónica sin valor externo visible. |

**Argumento detallado para la Opción A:**

1. **ADR-048 F2 es el siguiente paso natural de la secuencia**: F1 (eBPF sniffer + ML detector) está completo y validado. F2 (integrar Suricata como señal externa) es la progresión lógica hacia la arquitectura multi-engine del ADR-002.

2. **Valor científico inmediato**: El paper arXiv:2604.04952 ya documenta la comparativa Suricata vs aRGus offline. Integrar Suricata en el pipeline en vivo permite:
  - Datasets de correlación multi-engine (Zeek + Suricata + aRGus ML).
  - Métricas de latencia de detección comparada en tiempo real.
  - Validación del principio de "zero-coordination incident correlation" con señales heterogéneas.

3. **Terreno preparado**: Suricata ya está operativo en el Vagrantfile (`make up-suricata`), las 50,010 reglas ET Open están cargadas, y los experimentos offline (`make experiment-suricata-run`) están completos. La integración en el pipeline es el siguiente paso lógico.

4. **Principio rector**: "Calidad sobre fechas — los datasets se generan cuando el pipeline esté listo." La integración de Suricata acerca el pipeline al estado necesario para generar los datasets de valor científico comprometidos con UEx/INCIBE.

**Recomendación:** Proceder con DEBT-ARGUSPP-SURICATA-001 en DAY 162. Las opciones B, C y D se priorizarán en días posteriores según disponibilidad de hardware físico y madurez de los prerequisitos.

---

## Resumen del Consejo

| Pregunta | Veredicto |
|---|---|
| Q1 — Segundo test Wire Protocol | No necesario. Cobertura suficiente con tests existentes. |
| Q2 — Jenkinsfile.dev `agent any` | Correcto para fase actual. Migrar a `argus-server` cuando Jenkins esté en FEDER. |
| Q3 — Valores runtime vs fijos | Valores fijos por perfil. Runtime se reserva para post-FEDER. |
| Q4 — Tráfico sintético en E2E | No inyectar. Implementar fallback condicional (SKIP, no FAIL). |
| Q5 — Prioridad DAY 162 | **Opción A: DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2)**. |

---

**Principio rector recordado por el Consejo:** *"Un fix sin test de demostración es una promesa sin firma. Un test que falsea sus condiciones es una firma sin identidad."* — Qwen, DAY 124.

El Consejo queda a vuestra disposición para las deliberaciones del DAY 162.