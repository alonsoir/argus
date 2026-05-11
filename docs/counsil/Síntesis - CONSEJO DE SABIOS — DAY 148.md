**SÍNTESIS CONSEJO DE SABIOS — DAY 148 (8/8)**

---

**P1 — FRAMING DE COMPLEMENTARIEDAD EN ABSTRACT**

**Veredicto: 8/8 MANTENER EN ABSTRACT** — con un matiz léxico menor.

Consenso unánime: la afirmación es una contribución arquitectónica válida respaldada por los resultados experimentales (outputs ortogonales, capas de encoding distintas). No requiere integración implementada para ser defendible.

Refinamiento recomendado (ChatGPT, DeepSeek, Kimi, Qwen, Mistral convergentes):

Cambiar `"are complementary"` → `"are architecturally complementary"` o añadir `"by design"`. Una palabra, máximo blindaje ante revisores. DeepSeek propone la formulación más precisa:

> *"The three paradigms are complementary by design: Zeek's telemetry layer and Suricata's signature coverage operate alongside an ML behavioral classifier, each contributing at its native encoding layer."*

Acción: aplicar este cambio en v24 / próxima revisión. No urgente — no bloquea arXiv.

---

**P2 — DEBT-PARQUET-SCHEMA-001**

**(a) Granularidad: 8/8 — por flow.** Sin excepción. El pipeline ya opera sobre flows, el volumen por paquete es inmanejable, Neo4j modela relaciones no paquetes.

**(b) Política de registro:** Dividido en dos posiciones:
- **ChatGPT, Mistral, Kimi, Qwen (4/8):** Todos los eventos con flag de relevancia (`relevance_flag`) — máxima flexibilidad analítica, filtrar en ingesta Neo4j no en origen.
- **Claude, DeepSeek, Grok, Gemini (4/8):** Solo alertas/denies + muestreo 1% de normales — volumen controlado desde el nodo edge.

**Decisión recomendada:** posición híbrida — todos los eventos de `ml-detector` (necesarios para baseline behavioral), solo DENY/DROP de `firewall-acl-agent` (los ALLOW pueden ser órdenes de magnitud mayores). Decidir definitivamente con datos reales en la sesión Vagrant.

**(c) Tipos Arrow — consenso 8/8:**

| Campo | Tipo | Consenso |
|---|---|---|
| Timestamps | `int64` epoch ns UTC | 8/8 |
| Scores/confidence | `float32` | 8/8 |
| IDs pseudonimizados | `utf8` (dictionary-encoded) | 6/8 — Kimi y DeepSeek proponen `binary(32)` para producción |
| Enums (event_type, action) | `int8` o `dictionary(utf8)` | 8/8 |
| Puertos | `uint16` / `int32` | 8/8 |
| Bytes/packets | `int64` / `int32` | 8/8 |

---

**P3 — PRIORIDAD DAY 149**

**Veredicto: 8/8 — Opción A primero, sin debate.**

Secuencia acordada:

| Días | Tarea | Consenso |
|---|---|---|
| **DAY 149** | **A) DEBT-PARQUET-SCHEMA-001** | 8/8 bloqueante |
| **DAY 150-152** | **C) Vault prototype** (K_pseudo, Ed25519) | 7/8 antes que Jenkins |
| **DAY 153-155** | **B) Jenkins seed distribution** | 6/8 |
| **DAY 156+** | **D) ARM64 scope** | Solo si A+B+C verdes |
| **Buffer** | **E) Descanso** | ½ día cada 10 días |

**Dependencia oculta crítica (Qwen + DeepSeek):** Contactar Dr. Andrés Caro Lindo **esta semana** para iniciar DEBT-LEGAL-DATA-RETENTION-001 (dictamen GDPR) en paralelo. No bloquea el schema Parquet, pero sí el despliegue productivo — y el proceso jurídico tiene latencia externa.

**Regla de oro (Kimi):** No abrir ARM64 hasta que el pipeline x86_64 esté end-to-end verde. Portar antes de estabilizar multiplica bugs por dos arquitecturas.

---

**ACCIONES DAY 149:**

1. Levantar pipeline en Vagrant
2. Examinar CSVs reales `ml-detector` + `firewall-acl-agent`
3. Contar filas, confirmar columnas, decidir política de registro con datos reales
4. Generar schema Arrow v1.0, escribir Parquet de prueba, validar roundtrip
5. Documentar en ADR-0043 D4b, commit, cerrar DEBT-PARQUET-SCHEMA-001
6. Email Dr. Andrés Caro Lindo — iniciar DEBT-LEGAL-DATA-RETENTION-001