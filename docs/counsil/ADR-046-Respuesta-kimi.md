**Consejo de Sabios — Dictamen ADR-046**

Compañero, este ADR es ambicioso, bien estructurado, y tiene una contribución científica potencialmente significativa. Sin embargo, hay **tres puntos críticos que deben resolverse antes de aprobación**, uno de los cuales es un agujero metodológico que invalidaría la hipótesis científica si no se corrige.

---

## 🔴 Crítico — §8: El "descubrimiento empírico" carece de reproducibilidad

Tu §8.1–8.4 describe un experimento crucial: mezcla de datos sintéticos vs. académicos, con resultado sorprendente (el óptimo es el extremo puro). Pero:

> *"¿Los datos del experimento académico vs sintético existen en forma recuperable?"* — Pregunta 6 de tu propio ADR.

**Si la respuesta es "no", entonces la sección §8 no puede ir al paper v24 como resultado empírico.** Debe ir como **hipótesis motivadora** o **anécdota de diseño**, no como "evidencia empírica". Un reviewer de USENIX Security o NDSS pedirá:
- Curva F1 vs. ratio con intervalos de confianza.
- Descripción del procedimiento de muestreo.
- Código de generación de datos sintéticos.
- Métricas de robustez (¿el resultado se mantiene con diferentes seeds?).

**Veredicto:** Si no puedes reconstruir el experimento en ≤2 días, elimina la palabra "empírico" de §8 y refrasea como *"diseño motivado por observaciones preliminares durante el desarrollo"*. Si puedes reconstruirlo, hazlo **antes** de enviar v24 a arXiv. No dejes una afirmación empírica sin datos.

---

## 🔴 Crítico — §9.3: La "configuración mínima" no es viable económicamente

Tu tabla de combinaciones propone:

| Configuración | Hardware | Coste |
|---------------|----------|-------|
| Mínima | RPi5 solo | 90€ |
| Media | RPi5 + N100 | ~310€ |

**Problema:** Una RPi5 con aRGus + Suricata + Zeek + Wazuh no va a funcionar. Ni siquiera aRGus solo con ml-detector en RPi5 es viable para throughput de 100 Mbps (tu benchmark DAY 87 fue en VM con 6 vCPU/8GB, no en RPi5).

**Suricata en RPi5:** Suricata 6.0.10 con 50K reglas ET Open consume ~1GB RAM solo en carga de reglas, y CPU proporcional al throughput. En una RPi5 (8GB RAM, 4 cores @ 2.4GHz), aRGus sniffer (eBPF) + ml-detector (XGBoost inference) + Suricata + Zeek = **OOM o throttling garantizado** en cualquier tráfico >10 Mbps.

**Tu ADR debe ser honesto sobre esto:**

| Configuración | Hardware | Coste | Throughput esperado | Fuente |
|---------------|----------|-------|---------------------|--------|
| Mínima | N100 (4c/4t, 16GB) | ~150€ | 50 Mbps | Estimación DAY 154 |
| Media | N100 × 2 | ~300€ | 100 Mbps | Estimación |
| Completa | N100 + servidor central | ~460€ + hosting | 100 Mbps + correlación | Hardware FEDER |

**RPi5 debe salir de la tabla de configuraciones operativas.** Puede usarse para:
- Demo educativa (tráfico sintético lento).
- Sensor pasivo sin ml-detector (solo sniffer + Suricata sin reglas ET, modo "signature-only").
- Nodo de honeypot (OpenCanary).

Pero no para aRGus++ con las cuatro fuentes. Eso es un **overpromise** que un evaluador FEDER detectaría inmediatamente.

---

## 🟡 Importante — §3.3: `correlation-engine` en C++20 es correcto, pero el join ±500ms es ingenuo

Tu join temporal por 5-tupla con ventana ±500ms tiene tres problemas:

### 1. **NAT y proxies rompen la 5-tupla**
Si el hospital usa NAT saliente (casi seguro), la `src_ip` de aRGus es la IP privada del host, pero la `src_ip` de Zeek `conn.log` puede ser la IP pública post-NAT. La 5-tupla no coincide.

**Mitigación:** El join debe usar `anon_host_id` (HMAC de MAC) como clave primaria, no IP. La MAC es invariante ante NAT. Esto requiere que Suricata y Zeek reporten la MAC de origen, no solo la IP.

### 2. **DNS es previo al flow**
Un host resuelve `evil.com` a `1.2.3.4`, luego establece TCP a `1.2.3.4:443`. El DNS ocurre en t=-200ms, el flow en t=0. Tu ventana ±500ms los captura. Pero si el TTL del DNS es largo y el host reutiliza la resolución cacheada, el DNS puede ser de hace horas.

**Mitigación:** El join DNS→flow debe usar el TTL del registro DNS como ventana máxima, no un valor fijo. O, más simple: el `correlation-engine` mantiene un cache DNS local (IP→FQDN) con TTL respetado.

### 3. **Wazuh events no tienen 5-tupla**
Un evento de FIM (`/etc/passwd modificado`) o un login SSH no tienen `src_port` ni `dst_port`. Tu join por 5-tupla los excluye.

**Mitigación:** El join no es uno, son varios:
- **Join red:** aRGus ↔ Suricata ↔ Zeek por 5-tupla (±500ms) o por `anon_host_id` + timestamp.
- **Join host:** Wazuh por `anon_host_id` + timestamp (±5s, los eventos host no son tan precisos).
- **Join cruzado:** IP del flow → cache DNS → FQDN → Wazuh process que contactó ese FQDN (requiere que Wazuh logee conexiones de proceso, lo cual no hace por defecto).

**Recomendación:** Documenta en el ADR que el join es **jerárquico**, no una única operación. La v1 del `correlation-engine` solo implementa el join red (aRGus + Suricata + Zeek). El join host (Wazuh) es v2.

---

## 🟡 Importante — §7: `mitre-generator` debe ser ADR separado

Atomic Red Team es una herramienta externa compleja con sus propios requisitos (PowerShell en Windows, bash en Linux, dependencias como .NET). Integrarla en ADR-046 lo convierte en un monolito imposible de revisar.

**Recomendación:** Crea **ADR-047 — MITRE ATT&CK Experiment Orchestration** con:
- Alcance: solo el orquestador C++20 y el contrato de manifiesto JSON.
- Dependencias externas: Atomic Red Team (versión pinneada), Caldera (opcional).
- Seguridad: el orquestador corre en una VM aislada, no en la red de producción.
- Ética: autorización escrita del responsable de la instalación antes de ejecutar cualquier técnica.

ADR-046 debe referenciar ADR-047, no duplicarlo.

---

## 🟢 Menor — §13 Pregunta 4: Scope mínimo v1

**Respuesta:** aRGus + Suricata como v1 mínima. Suricata aporta:
- Etiquetado automático de alta confianza (reglas ET).
- Ground truth inmediato sin necesidad de MITRE scripts.
- Validación de la hipótesis científica con dos fuentes en lugar de cuatro.

Zeek es v1.5 (añade contexto de protocolo). Wazuh es v2 (añade visibilidad host). Esta secuenciación permite validar incrementalmente y no bloquea FEDER si Wazuh no cabe en el hardware.

---

## 🟢 Menor — §13 Pregunta 5: Atomic Red Team como dependencia externa

**Sí, dependencia externa pinneada.** No reimplementes técnicas ATT&CK. Atomic Red Team tiene ~1,000 tests atómicos mantenidos por la comunidad. Tu valor añadido es el orquestador C++20 que selecciona, temporiza, y etiqueta — no los scripts de ataque.

En `docs/deps/`:
```
atomic-red-team/
  version: "1.45.0"
  source: "https://github.com/redcanaryco/atomic-red-team"
  license: "MIT"
  hash: "sha256:..."
```

---

## Resumen de acciones antes de aprobación

| Item | Severidad | Acción |
|------|-----------|--------|
| §8 "empírico" sin datos | **Bloqueante** | Reconstruir experimento en ≤2 días, o refrasear como hipótesis motivadora |
| RPi5 en tabla de configuraciones | **Bloqueante** | Eliminar RPi5 de configuraciones operativas; restringir a demo/educativo |
| Join jerárquico documentado | Importante | Aclarar que v1 = join red, v2 = join host; NAT/MAC como clave primaria |
| ADR-047 separado | Importante | Extraer `mitre-generator` a ADR propio |
| Scope v1 = aRGus + Suricata | Menor | Documentar secuenciación en §13 |

---

## Veredicto preliminar

**ADR-046 es aprobable con enmiendas.** La dirección es correcta: aRGus++ como NDR/EDR híbrido es la evolución natural del proyecto y justifica el modelo enterprise. Pero el ADR debe ser honesto sobre limitaciones de hardware y honesto sobre la evidencia empírica.

**No envíes a arXiv v24 con §8 como "evidencia empírica" sin los datos.** Eso es el tipo de error que un reviewer usa para rechazar el paper completo, independientemente de la calidad del resto.

*El Consejo ha hablado. Que la ambición no eclipse la honestidad metodológica.* 🛡️