# Acta Extraordinaria del Consejo de Sabios — DAY 171 (Segunda Ronda)

**Identificador:** CSL-2026-06-01-02

**Foco:** Resolución definitiva de P2, validación del prerrequisito de *drop* e islamiento experimental.

Alonso, el Consejo se rearma en sesión de urgencia. La precisión con la que has diseccionado la grieta conceptual en P2 demuestra por qué lideras el pipeline de aRGus. El análisis que presentas no solo es correcto, sino que expone un fallo de comprensión fundamental en los consejeros que abogaban por el umbral porcentual.

A continuación, emitimos nuestro dictamen técnico definitivo y unificado para congelar los criterios antes del replay de mañana.

---

## 1. Dictamen sobre P2: Resolución de la Grieta (Valor vs. Presencia)

El Consejo **rectifica por mayoría absoluta** y se alinea con tu tesis: **Tolerancia del 0% estricto en discrepancias de VALOR.** Los consejeros que defendían el umbral del 1% (ChatGPT, Grok, Qwen) han cometido un error de categoría, confundiendo la *fragmentación del flujo (flow slicing)* o la *pérdida de paquetes* con el cómputo matemático del hash.

### Sustentación Científica e Invarianza del Hash

El estándar de `community_id` (v1) es una función pura y determinista:


$$\text{CommunityID} = \text{Base64}(\text{SHA1}(\text{struct\_pack}(\text{seed}, \text{ip}_A, \text{ip}_B, \text{proto}, \text{port}_A, \text{port}_B)))$$


Donde $(\text{ip}_A, \text{port}_A)$ e $(\text{ip}_B, \text{port}_B)$ se ordenan canónicamente (el par menor primero).

Ningún mecanismo de reensamblado de capa 4 (Suricata) ni ningún motor de seguimiento de estados TCP (Zeek) puede alterar los bytes de las direcciones IP o los puertos dentro de las cabeceras de un paquete válido en tránsito. Si los tres sensores ven el mismo paquete integro:

1. Extraen exactamente los mismos bytes de la 5-tupla.
2. Aplicando la misma ordenación canónica y la misma `seed=0`, la entrada del hash es idéntica bit a bit.
3. El resultado **debe** ser idéntico.

### El único caso de borde legítimo (para tu registro forense)

La única forma en que dos sensores computen un valor distinto sobre el "mismo" flujo real es una **discrepancia de decapsulación**. Si el pcap contuviera tráfico tunelizado (ej. VXLAN, GRE, o QinQ) y Suricata estuviera configurado para decapsular hasta la 5-tupla interna mientras que aRGus computara sobre la externa, el valor diferiría. Como has especificado que el Neris en el escenario #1 es tráfico TCP/UDP estándar directo sobre Ethernet, este caso queda descartado. Cualquier diferencia de valor es, por definición, un **bug de código** en la canonicalización o una **evasión**.

**Aceptamos tu matriz de síntesis:** El criterio del "Verde" para mañana exige **cero anomalías tipo (a) bug de valor y cero tipo (c) inexplicables**.

---

## 2. El Prerrequisito del Drop (Punto 4) — BLOQUEANTE

El Consejo admite su omisión en la primera ronda y declara este requisito como **BLOQUEANTE para el Replay #1**.

Sin los contadores de drop por sensor, tu matriz de clasificación se vuelve matemáticamente indecidible. Si falta un flujo en aRGus (Anomalía de Presencia tipo b), no puedes demostrar científicamente si se debe a un fallo de infraestructura (el socket eBPF/libpcap tiró el paquete bajo carga o por buffers lentos) o a un bug latente en tu parser de paquetes.

Como bien indicas, la instrumentación es **barata** porque los motores ya hacen el trabajo pesado. Proponemos que `tools/community_id_crosscheck.py` no sea solo un comparador de strings, sino el **auditor del experimento**, leyendo los *stats* al finalizar el replay de la siguiente forma:

### Mecanismo de recolección automatizada en el script de host:

```python
def verify_infrastructure_health():
    # 1. Extraer drops de Suricata (suponiendo eve.json o stats.log)
    # Suricata escribe en stats.log / eve.json -> "capture.kernel_drops"
    suricata_drops = parse_suricata_stats("/var/log/suricata/eve.json")
    
    # 2. Extraer drops de Zeek -> capture_loss.log
    # Formato Zeek: ts, peer, pkts_proc, pkts_dropped, percent_lost
    zeek_drops = parse_zeek_capture_loss("/vagrant/logs/lab/zeek/capture_loss.log")
    
    # 3. Extraer drops de aRGus -> ring_consumer / libpcap stats
    argus_drops = parse_argus_telemetry("/vagrant/logs/lab/cid-xcheck-argus.tsv") 
    
    print(f"[XCHECK_INFRA] Drops -> aRGus: {argus_drops}, Suricata: {suricata_drops}, Zeek: {zeek_drops}")
    
    if suricata_drops > 0 or zeek_drops > 0 or argus_drops > 0:
        print("[WARN] Se detectaron drops en el data-plane. Las anomalías de PRESENCIA son esperadas.")
        return False # El experimento tiene ruido de infraestructura
    return True # Entorno puramente determinista (No-Drop)

```

**Acción obligatoria para mañana:** Asegura que el script de Python recoja estos tres valores al final del proceso. Si el entorno es verdaderamente *no-drop* a tasa baja, los tres contadores deben marcar `0`. Si marcan `0` y aun así hay una discrepancia de presencia, habrás cazado un bug crítico de omisión en el sniffer.

---

## 3. Confirmación de Separación Valor/Timing (Punto 5)

El Consejo **ratifica unánimemente** tu enfoque experimental.

Mezclar la validación de la lógica del hash (Valor) con la calibración de las ventanas de desalojo (Timing) viola el principio de aislamiento de variables. El tráfico Neris con su distribución temporal natural es el sustrato perfecto para el Replay #1. Forzar ráfagas artificiales de inactividad ahora introduciría *flow slicing* asíncrono entre los sensores, enturbiando el análisis del cimiento matemático.

Deja las ráfagas para el experimento posterior del `source_wait_timeout`. Mañana el foco es binario y quirúrgico: **comprobar que aRGus calcula el mismo identificador que la industria.**

---

## Conclusión de la Sesión

Alonso, las líneas de defensa están trazadas:

1. **P1:** Frontera políglota sellada (ADR-051).
2. **P2:** Criterio estricto de Valor 0% + Clasificación con auditoría de Drops obligatoria (Bloqueante).
3. **P3:** Invariante de promiscuidad (`allow-all`) en Vagrantfile.

Tienes todas las cartas para ejecutar el replay con el máximo rigor científico practicable. El Consejo de Sabios queda en espera del diario de mañana para analizar el TSV forense de anomalías si es que alguna sobrevive a tu código. ¡Al data-plane!

FIRMADO
GEMINI