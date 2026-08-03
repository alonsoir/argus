# Contrato `host_domain_v1` — puerta de diseño (Wazuh → grafo host)

**Proyecto:** aRGus NDR · **Rama:** `feat/zeek-to-graph` · **Fecha:** DAY 240
**Paso del cierre:** 2 — arrancar el contrato del dominio host
**Evidencia:** `docs/design/host-domain-contract/evidencia/alerts-day240-snapshot.json` (50 eventos, congelado)

Cada afirmación va marcada **[MEDIDO]** (sale de comando/fichero), **[DECISIÓN]** (elección de Alonso)
o **[PENDIENTE]** (por medir o por decidir). Regla de la casa: HECHO ≠ SOSPECHADO.

---

## 0. Propósito y encuadre

- **[DECISIÓN]** Wazuh es el 4º sensor pero **NO es de red**: es dominio HOST (HIDS/EDR). Su dato va a
  SU PROPIO grafo / SU PROPIA BD Kuzu bajo el contrato `host_domain_v1`, **nunca** al `$KUZU` de red
  compartido de `mitre-start`. Ratifica DAY 225 y `DEBT-HOST-DOMAIN-CONTRACT-001`.
- **[MEDIDO]** El pipeline de red quedó cerrado con 3 sensores (aRGus + Suricata + Zeek). Wazuh es la
  mitad host del híbrido (ADR-046) y encaja con el ángulo Matzinger del paper: el movimiento lateral y
  la escalada de privilegio son **señales de daño**, no features de paquete.

---

## 1. Evidencia medida y sus límites

- **[MEDIDO]** El snapshot se tomó del `alerts.json` de la VM `wazuh` con **manager (000) + un agente
  real (002/zeek)** enrolado y `Active`. Rompe la degeneración de DAY 238, donde solo existía el
  agente 000 auto-monitorizándose.
- **[MEDIDO]** 50 eventos, **0 líneas ilegibles** → el fichero es **JSON-por-línea** (un evento = una
  línea). Este es el formato que el adapter debe asumir.
- **[MEDIDO]** El fichero es **live y crece** (se observó 25 líneas y minutos después 50 eventos): son
  sesiones PAM abriéndose y cerrándose sin parar por `journald`.
- **[AVISO honesto]** Este snapshot es **dato de diseño**, NO la evidencia reproducible del paper. La
  evidencia del paper nace de `vagrant destroy -f && vagrant up` + MITRE. Además, los eventos aquí
  proceden de actividad **ordinaria de provisioning** (vagrant/sudo/ssh), no de un ataque.

---

## 2. Inventario de lo que emite Wazuh — [MEDIDO]

### 2.1 Reparto por agente
| agent.id | name        | ip               | eventos |
|----------|-------------|------------------|---------|
| 000      | argus-wazuh | (local, sin ip)  | 35      |
| 002      | zeek        | 192.168.100.11   | 15      |

La atribución de host real funciona: el 002 aporta con su propia identidad e IP.

### 2.2 Reglas presentes (baseline = autenticación/sesión)
| rule.id | nivel | descripción                         | nº |
|---------|-------|-------------------------------------|----|
| 5502    | 3     | PAM: Login session closed           | 18 |
| 5501    | 3     | PAM: Login session opened           | 15 |
| 5402    | 3     | Successful sudo to ROOT             | 7  |
| 5715    | 3     | sshd: authentication success        | 5  |
| 533     | 7     | Listened ports (netstat) changed    | 3  |
| 502     | 3     | Wazuh server started                | 1  |
| 503     | 3     | Wazuh agent started                 | 1  |

- **[MEDIDO]** `rule.groups`: syslog 45 · pam 33 · authentication_success 20 · sudo 7 · ossec 5 · sshd 5.
- **[MEDIDO]** `location`: journald 45 · netstat 3 · wazuh-monitord 1 · wazuh-agent 1.
- **[CORRECCIÓN a DAY 238]** NO aparece **ningún** evento FIM/syscheck, rootcheck ni SCA en esta
  ventana. El baseline de un agente recién levantado es higiene de autenticación, no integridad de
  fichero. (FIM/SCA emergen con cambios de fichero o scans — ver §7 P1.)

### 2.3 Claves de nivel superior (freq / 50)
`timestamp, rule, agent, manager, id, full_log, decoder, location` = 50/50 ·
`data` = 46/50 · `predecoder` = 45/50 · `previous_output` / `previous_log` = 3/50.

### 2.4 Regalo medido: MITRE ATT&CK y cumplimiento **nativos por regla**
- **[MEDIDO]** `rule.mitre` viene poblado de fábrica:
    - `5402` sudo→ROOT → **T1548.003** (Privilege Escalation, Defense Evasion)
    - `5501` PAM login → **T1078** (Valid Accounts)
    - `5715` sshd success → **T1078 + T1021** (Valid Accounts + Remote Services); tácticas incluyen
      **Lateral Movement** de forma literal.
- **[MEDIDO]** Cada regla trae mapeo de cumplimiento: `pci_dss, gdpr, hipaa, nist_800_53, tsc, gpg13`.
- **[MEDIDO]** El mapeo MITRE/cumplimiento es **por regla y estático** → se normaliza en nodos `Rule`
  y `MitreTechnique`, no se duplica en cada evento.

### 2.5 `data` es una bolsa variable por regla
| rule.id | data observada                                             |
|---------|------------------------------------------------------------|
| 5715 sshd | `srcip=10.0.2.2`, `srcport`, `dstuser`                    |
| 5402 sudo | `srcuser`, `dstuser`, `pwd`, `command`                    |
| 5501 PAM  | `dstuser`, `uid`                                          |
| 5502 PAM  | `dstuser`                                                 |
| 503       | `extra_data="zeek->any"`                                  |
| 533, 502  | **sin `data`** — payload en `previous_output`/`full_log` como texto |

- **[MEDIDO]** Un evento host **puede traer coordenada de red**: el sshd carga el `srcip/srcport` del
  origen del login (breadcrumb de movimiento lateral). Se queda en la BD host; **no** se une al `$KUZU`
  de red (invariante).

### 2.6 Identidad de host: dos nombres distintos
- **[MEDIDO]** `agent.name = "zeek"` (nuestro `WAZUH_AGENT_NAME`, identidad **elegida**) vs
  `predecoder.hostname = "argus-zeek"` (hostname real del SO). Son dos.
- **[MEDIDO]** `timestamp` top-level es ISO8601 con millis+TZ (`2026-07-31T03:22:09.071+0000`) en los
  50 eventos. `predecoder.timestamp` es syslog sin año (lossy) → no vale como identidad.

### 2.7 `id` de Wazuh
- **[MEDIDO]** `id` top-level = `<epoch_seconds>.<byte_offset_en_el_log>` (p.ej. `1785468156.2917`).
  50/50 **único** en esta corrida; el offset crece monótono y desempata dentro del mismo segundo.
- **[MEDIDO]** El offset es posición en el fichero → estable al **re-ingerir el mismo** `alerts.json`,
  **no** estable tras `destroy&up` (otros id).

---

## 3. Decisiones de diseño — [DECISIÓN]

- **D1 — Dominio y BD separados.** `host_domain_v1` es un contrato propio, su BD Kuzu propia. Wazuh es
  el único escritor de ese grafo → no hay colisión cross-sensor dentro de él.
- **D2 — event_id = hash de la línea cruda.** `event_id = "wz1:" + base64_std(BLAKE2b-256(TAG ‖
  raw_line))`, con `TAG = "argus-hostevent-v1"` y `raw_line` = los bytes exactos de la línea JSON.
    - Idempotente por fichero: re-ingerir el mismo snapshot da el mismo `event_id` → el `MERGE` no
      duplica.
    - Cada `destroy&up` genera líneas nuevas → `event_id` nuevos. Es **correcto**: son sesiones
      genuinamente nuevas.
    - Mismo linaje que `flow_uid` (tag de versión + BLAKE2b-256 + base64), namespaced con `wz1:` para
      que sea visiblemente distinto del espacio de event_id de red.
    - El `id` crudo de Wazuh se conserva como propiedad de procedencia (`wazuh_alert_id`), **no** como PK.
- **D3 — PK del nodo `Host` = `agent.id`.** Es el identificador más estable. `name`, `ip` y
  `os_hostname` (= `predecoder.hostname`) son propiedades + cross-check.
- **D4 — Identidad del evento = host + regla + timestamp**, NO 5-tupla. El `event_id` de D2
  operacionaliza esa identidad.
- **D5 — `data` como property flexible + subconjunto común extraído.** No se aplana en columnas fijas;
  se guarda el `data` completo (JSON) y se extraen las claves comunes de auth: `srcuser, dstuser,
  srcip, srcport, uid, command`.
- **D6 — El adapter lee incrementalmente por watermark.** El fichero es append-only y live; el adapter
  persiste el último offset y lee de ahí a EOF. Para el camino reproducible del paper (`destroy&up`)
  lee el fichero fresco entero.
- **D7 — MITRE/cumplimiento normalizados por regla** (nodos `Rule` y `MitreTechnique`), no por evento.

---

## 4. Esquema propuesto del grafo host

### Nodos
- **`Host`** — PK `host_id` (= `agent.id`). Props: `name`, `ip`, `os_hostname`.
- **`HostEvent`** — PK `event_id` (D2). Props: `timestamp` (ISO), `rule_id`, `level`, `decoder`,
  `location`, `full_log`, claves comunes (`srcuser, dstuser, srcip, srcport, uid, command`),
  `data_json` (fidelidad completa), `wazuh_alert_id` (procedencia).
- **`Rule`** — PK `rule_id`. Props: `level`, `description`, `groups[]`.
- **`MitreTechnique`** — PK `technique_id` (T1078…). Props: `name`, `tactics[]`.
- **`Control`** *(opcional, ver P4)* — PK `(framework, control_id)`. Framework ∈ {pci_dss, gdpr, hipaa,
  nist_800_53, tsc, gpg13}.

### Aristas
- `(HostEvent)-[:ON_HOST]->(Host)` — vía `agent.id`.
- `(HostEvent)-[:MATCHED]->(Rule)` — vía `rule.id`.
- `(Rule)-[:MAPS_TO]->(MitreTechnique)` — el mapeo vive en la regla.
- `(Rule)-[:REQUIRES]->(Control)` *(opcional)*.

---

## 5. Campos del contrato `host_domain_v1` (fila que emite el adapter)

**Producidos por nosotros**
`schema_version="host_domain_v1"` · `source_sensor="wazuh"` · `event_id` (D2) · `host_id`(=agent.id) ·
`hmac_row` *(ver P3)*

**Copiados de Wazuh**
`wazuh_alert_id`(=id) · `timestamp` · `agent_id/agent_name/agent_ip` · `os_hostname` ·
`rule_id/rule_level/rule_description/rule_groups[]` · `decoder_name` · `location` · `full_log` ·
`data_json` + comunes extraídas · `mitre_ids[]/mitre_tactics[]/mitre_techniques[]` ·
`pci_dss[]/gdpr[]/hipaa[]/nist_800_53[]/tsc[]/gpg13[]`

---

## 6. Objeciones y riesgos

- **O1 — Rotación de logs.** Wazuh rota `alerts.json`; un watermark por offset se rompe en la rotación.
  Mitigación por (inode, offset) o por el prefijo de segundos del `id`. → **[PENDIENTE] P2**.
- **O2 — Formas de `data` no medidas.** FIM/SCA/rootcheck no aparecieron; sus claves de `data` no están
  cubiertas por las comunes extraídas. Aceptable: `data_json` las absorbe; las comunes se amplían al
  medirlas.
- **O3 — event_id no estable entre regeneraciones.** Por diseño (D2): sesiones nuevas = eventos nuevos.
  Consecuencia: no se puede correlacionar "el mismo login" entre dos `destroy&up`. No es requisito.
- **O4 — Integridad tipo ledger.** El bronce de red firma cada fila (`hmac_row`). Decidir si el dominio
  host replica esa disciplina. → **[PENDIENTE] P3**.

---

## 7. Pendientes — [PENDIENTE]

- **P1 — FIM/SCA/rootcheck.** Provocarlos con técnica MITRE host-touching en `mitre-start` (paso 3),
  medir su forma de `data` y ampliar el contrato. Sin esto, el grafo host solo muestra higiene de auth,
  no "Wazuh cazó el ataque".
- **P2 — Rotación de `alerts.json`** en el watermark del adapter (O1).
- **P3 — `hmac_row`/integridad** del dominio host y su provisión de clave
  (`DEBT-BRONZE-KEY-PROVISIONING-001`). Inclinación: paridad con el bronce de red, a confirmar.
- **P4 — Nodos `Control`/cumplimiento**: implementar o diferir. Útil para el encuadre hospitalario
  (HIPAA/GDPR); no bloquea el pipeline.
- **P5 — ¿bronce/oro (Parquet) o directo a Kuzu?** El pipeline de red va bronce→oro→Kuzu (ledger
  append-only, grafo reconstruible = Vía Appia). Decidir si el host replica ese ledger o carga directo.

---

## 8. Plan de implementación (batallas siguientes, no hoy)

1. **`wazuh-adapter/`** — scaffold siguiendo el estándar de `suricata-adapter/` y `zeek-adapter/`:
   `alerts.json` → filas `host_domain_v1`. Resuelve P5 (ledger vs directo) al arrancar.
2. **`schema.cypher`** del grafo host — las tablas de nodo/arista de §4.
3. **`host_parquet_to_kuzu_loader`** (o cargador directo) — espejo de `parquet_to_kuzu_loader`.
4. **Cableado en `mitre-start`** — con su **`$KUZU_HOST` propio**, separado del `$KUZU` de red.
5. **Gate**: integrar en EMECAS+++, ver datos llegando al grafo host, EMECAS+++ en verde → **merge a
   main** (probar en `feat/zeek-to-graph` primero).