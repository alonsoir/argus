# PROPUESTA AL CONSEJO DE SABIOS — Auditoría de features de los modelos ML

**DAY 209 · Reconocimiento (no desarrollo)**
**Disparador:** línea de investigación MITRE ATT&CK / Atomic Red Team para el
detector de ransomware inerte (`DEBT-RANSOMWARE-ML-HEAD-INERT-001`).
**Resultado:** el reconocimiento derivó en una auditoría del contrato de features
de todos los modelos del ml-detector. El diagnóstico del ransomware inerte cambia
respecto a lo que dicen los DEBT existentes, y aparece un hallazgo colateral en el DDoS.

**Método:** rastreo del codebase real (medir, no votar). Fuentes leídas:
`ml-detector/config/ml_detector_config.json`,
`ml-detector/include/feature_extractor.hpp`,
`ml-detector/src/feature_extractor.cpp` (parcial — ver §6),
`ml-detector/include/ml_defender/ransomware_detector.hpp`,
`ml-detector/models/production/level3/ransomware/ransomware_network_detector_proto_aligned.json`.
Nada aquí es de memoria; todo se traza a un fichero.

---

## 1. Estado del sistema (medido)

El ml-detector es tricapa. Todos los extractores de features reciben
`protobuf::NetworkFeatures` — es decir, **solo lo que el sniffer observa en el
cable** (`eth1`). Ningún extractor recibe telemetría de host.

| Modelo | Nivel | Tipo | Features | Dominio de las features |
|---|---|---|---|---|
| attack_detector | L1 | ONNX RandomForest (+scaler) | 23 | red |
| ddos | L2 | RandomForest embebido C++ | 10 | red (con 3 constantes — §3) |
| **ransomware** | L2 | RandomForest embebido C++ | 10 | **host (9 de 10) — §2** |
| web/traffic | L3 | RandomForest embebido C++ | 10 | red |
| internal | L3 | RandomForest embebido C++ | 10 | red (lateral, exfil, discovery) |

Los modelos migraron de ONNX a RandomForest embebido en C++ (árboles inline:
`ddos_trees_inline.hpp`, `traffic_trees_inline.hpp`, `internal_trees_inline.hpp`);
solo L1 sigue en ONNX. El detector de ransomware NO tiene su
`ransomware_trees_inline.hpp` junto a sus hermanos — su arquitectura embebida vive
en `src/ransomware_detector.cpp` / `libransomware_detector.a`.

---

## 2. Hallazgo principal: el detector de ransomware pide features de host

`ransomware_detector.hpp` declara 10 features y su importancia. **Nueve de las diez
son de host**, no de red:

```
entropy            36%  ← LA MÁS CRÍTICA
resource_usage     25%
io_intensity       24%
network_activity    8%  ← única feature legítimamente de red
file_operations     2%
access_frequency    2%
behavior_consistency 2%
data_volume         1%
process_anomaly    <1%
temporal_pattern   <1%
```

El modelo fue entrenado sobre features de comportamiento de host: entropía de
**ficheros cifrados en disco**, intensidad de **I/O de disco**, operaciones de
**fichero**. Pero en producción recibe `NetworkFeatures`. El extractor
(`extract_level2_ransomware_features`, líneas 272–312) resuelve el desajuste
**fabricando proxies de red sin correlación con lo que el modelo aprendió**:

```cpp
// [1] entropy — ⭐ MOST IMPORTANT (36% feature importance)
// Usar packet length variance como proxy de entropía
features[1] = std::min(pkt_variance / 100000.0f, 2.0f);

// [4] file_operations — Proxy: PSH flags
// [5] process_anomaly — Proxy: ACK flag ratio
```

La feature que decide el 36% del modelo —entropía de ficheros— se aproxima con la
**varianza de longitud de paquete**. No correlacionan. La única feature de red
semánticamente correcta (`network_activity` = paquetes/s) pesa el 8%.

**Diagnóstico (corrige los DEBT existentes):** el detector de ransomware no está
inerte por falta de señal de entrenamiento (`DEBT-RANSOMWARE-ML-HEAD-INERT-001`),
sino por **desajuste de dominio en el adaptador de features**: un modelo de host
enchufado a una fuente de red mediante proxies que no significan nada. Y no se
arregla reentrenando con más tráfico de red, porque el fenómeno que el modelo
detecta —cifrado de ficheros en disco— **no cruza `eth1` por definición**. Es
irrescatable en su forma actual dentro de un NDR.

*Nota de alcance:* leímos features [0]–[5]. Las cuatro restantes
(`temporal_pattern`, `access_frequency`, `data_volume`, `behavior_consistency`)
no se inspeccionaron, pero son conceptos de host y presumiblemente más proxies.

---

## 3. Hallazgo colateral: el DDoS tiene 3 features constantes muertas

Misma arquitectura que el ransomware (RandomForest embebido, 10 features), pero el
DDoS es un fenómeno de red puro, así que sus features **pueden** salir de datos
reales. Y en su mayoría salen — pero tres no
(`extract_level2_ddos_features`, líneas 224–264):

```cpp
// [2] Source IP Dispersion (using protocol variety as proxy)
features[2] = normalize(1.0f, 0.0f, 10.0f);        // constante: siempre 0.1

// [3] Protocol Anomaly Score
float protocol_anomaly = (1.0f > 5) ? 1.0f : 0.0f;  // (1.0>5) es SIEMPRE false
features[3] = protocol_anomaly;                      // constante: siempre 0.0

// [7] Geographical Concentration (placeholder)
features[7] = 0.5f;                                  // constante
```

`feature[3]` es una comparación que el compilador resuelve a `false` en tiempo de
compilación: esa feature vale `0.0` en toda inferencia, para siempre.

Balance del DDoS: seis features reales confirmadas (0,1,4,5,6,8 — ratios de flags,
simetría, amplificación, completación, escalación), tres constantes (2,3,7), una sin
verificar (9, `resource_saturation`, cortada en línea 264). **A diferencia del
ransomware, el DDoS funciona en lo esencial**: sus features de mayor peso
(`syn_ack_ratio`, `packet_symmetry`) son legítimas, y un DDoS es detectable con red
pura. Está **degradado, no muerto**. No es urgente; es deuda a registrar.

---

## 4. El segundo modelo de ransomware (`proto_aligned`) es un callejón sin salida

En `models/production/level3/ransomware/` conviven artefactos de un intento
anterior: un XGBoost de red, `ransomware_network_detector_proto_aligned`. El nombre
sugería una versión de red reconectable. **No lo es:**

```json
"input_shape": [1, 45],
"feature_names": ["feature_0", "feature_1", ... "feature_44"],
"conversion_method": "direct_conversion"
```

45 features **anónimas**, sin contrato documentado, convertidas "a pelo" desde algún
notebook. No se puede alimentar 45 ranuras que nadie sabe qué son. Es un artefacto
muerto: candidato a borrado, pero **con DEBT que documente por qué existió y por qué
se abandona antes de eliminarlo** (principio: las discrepancias afloran como DEBT, no
se resuelven en silencio; y `git rm`, no `rm`, para preservar el historial).

---

## 5. El contraste es la prueba, y la frontera es el resultado

**Misma arquitectura de modelado, resultados opuestos.** DDoS y ransomware son ambos
RandomForest embebido de 10 features. El DDoS funciona (fenómeno de red, features de
red); el ransomware no (fenómeno de host, features de host fabricadas desde red). Esto
demuestra que el problema **no es la técnica de modelado** (los RandomForest embebidos
son sanos), sino **el dominio de las features**. Es un diagnóstico limpio y defendible.

De ahí la frontera arquitectónica, que no es un bug sino un hecho a medir y publicar:

- aRGus es un **NDR**. Ve las **fases de red** del ciclo de vida de un ransomware
  —C2/beaconing, network discovery (T1046), lateral movement (T1021), exfiltración
  (T1048)— a través de los detectores `internal`, `web`, `level1`, que sí consumen
  `NetworkFeatures` reales.
- aRGus **NO** ve el **acto de cifrado** en sí (T1486): es un fenómeno de host
  (entropía en disco) que no cruza el cable. Ningún NDR lo ve —ni aRGus, ni Suricata,
  ni Zeek— por construcción.
- **Wazuh (HIDS) sí lo ve**: mira ficheros, syscalls, procesos. Las nueve features de
  host que el detector de ransomware pide son, casi una a una, lo que un HIDS observa.

Esto reencuadra la pregunta de Andrés: no es "¿aRGus detecta ransomware?" (binario
engañoso), sino **"¿qué capa de la defensa ve qué fase del ataque?"** — una matriz con
huecos honestos, más fuerte científicamente que cualquier número inflado.

---

## 6. Lo que NO medimos (honestidad epistémica)

- Features [6]–[9] del ransomware y [9] del DDoS: no inspeccionadas (código no leído).
- **Comportamiento en runtime**: qué modelo carga de verdad el binario vs lo que
  declara el config. Verificable con una ejecución instrumentada; no hecho hoy.
- Los árboles embebidos y los datos de entrenamiento originales: no auditados.
- Ninguna de estas lagunas cambia el diagnóstico de §2 (el desajuste de dominio es
  estructural, visible en las firmas de tipo y en los proxies leídos), pero acotan
  qué afirmamos con certeza.

---

## 7. Propuesta de acción — línea MITRE ATT&CK / Atomic Red Team

Para generar datos comportamentales **reales, legales y publicables** sin malware ni
laboratorio de contención: emular técnicas documentadas de un ransomware nombrado
(p. ej. perfil de técnicas de LockBit, ya cartografiado por terceros) con **Atomic
Red Team** (Red Canary; open source MIT, mantenido, tests <5 min, con atomics Linux).

**Montaje** (reutiliza la topología de los replays CTU-13): los atomics se lanzan
desde la VM `client` —diseñada precisamente para inyectar tráfico— y `defender`
observa en `eth1`, igual que con los pcap relays.

**Diseño: matriz técnica × sensor × componente (ablación).** Filas = sensores
(aRGus con sus cabezas activables una a una, Suricata, Zeek, Wazuh). Columnas =
técnicas ATT&CK. Se activan/desactivan componentes para medir qué se cae. Resultado
esperado y **publicable**:

- Técnicas de red (C2, discovery, lateral, exfil) → las cazan los NDR (aRGus/Suricata/Zeek).
- Cifrado y borrado de shadow copies (host) → invisibles a los NDR por diseño; los
  caza Wazuh.

Ese reparto, con sus huecos declarados, es el entregable que apoya la solicitud a
Andrés. La emulación **no rescata** el modelo muerto de §2; genera la señal para
entrenar un modelo comportamental nuevo y honesto, y valida empíricamente la frontera.

---

## 8. Preguntas concretas al Consejo (para deliberación)

1. **¿Desactivar la cabeza de ransomware embebida actual** (`enabled: false` en
   config)? Sus proxies producen scores engañosos; mantenerla "activa" contamina
   cualquier veredicto. Alternativa: mantenerla con etiqueta explícita
   "proxy-based, no fiable". *(Probablemente requiere ADR.)*

2. **¿Registrar `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001`** (XGBoost de 45 features
   anónimas) y autorizar su borrado posterior vía `git rm`, documentando por qué
   existió?

3. **¿Registrar `DEBT-DDOS-FEATURES-CONSTANT-001`** (features [2],[3],[7] constantes)
   sin acción inmediata? El DDoS funciona en lo esencial; arreglar o justificar esas
   tres es otra batalla.

4. **¿Autorizar entrenar un modelo comportamental de ransomware DE VERDAD?** Y la
   pregunta de diseño que define el tamaño del compromiso:
    - **Opción A — modelo de red**: entrenable con lo que aRGus ya observa, emulable
      con Atomic Red Team, dentro del alcance pre-FEDER. Detecta las fases de red del
      ransomware, no el cifrado.
    - **Opción B — modelo híbrido red+host**: requiere integrar telemetría de Wazuh al
      pipeline. Detectaría también el cifrado, pero es mucho más ambicioso y
      probablemente **post-FEDER**.

5. **¿Aprobar la línea MITRE ATT&CK / Atomic Red Team** (§7) como trabajo real
   pre-FEDER, con la matriz de ablación como entregable para Andrés?

---

*Via Appia Quality — medir, no votar. Un escudo que conoce sus propias sombras.*
