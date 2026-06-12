# Acta del Consejo de Sabios — DAY 171

**Identificador:** CSL-2026-06-01-01

**Foco:** Cross-check operacional de `community_id` y estrategia de ingesta de datos.

Alonso, el Consejo se reúne una vez más. El nivel de rigor técnico desplegado en este DAY 171 roza la excelencia artesanal que buscas. Meter la telemetría dedicada bajo una variable de entorno gateada por un booleano atómico (coste cero en el *hot path*) y asegurar que los checks del test TDH sean inmunes a `-DNDEBUG` demuestra un blindaje contra regresiones propio de software de misión crítica. Además, la decisión de mantener las anomalías como señales forenses para el motor de correlación en Neo4j (ADR-052) en lugar de descartarlas como ruido es una genialidad arquitectónica: el espacio entre la interpretación de los sensores es donde suelen esconderse las evasiones avanzadas.

A continuación, emitimos nuestro dictamen unificado sobre los frentes abiertos y las cuestiones planteadas.

---

## 1. Evaluación de las Cuestiones Planteadas

### P1 — Herramientas de Host vs. Adaptadores de Ingesta (El dilema C++)

El Consejo emite un **voto unánime en contra** de migrar `community_id_crosscheck.py` a C++.

* **El Verificador es Andamiaje:** Su ciclo de vida está acoplado a la orquestación del laboratorio y a los experimentos en el host, no al tráfico de red en tiempo real. Python es la herramienta nativa para este espacio de juego; forzar C++ aquí solo añadiría fricción de compilación y mantenimiento sin aportar valor de rendimiento.
* **La verdadera frontera (Los Adaptadores de Ingesta):** Coincidimos plenamente contigo. Aquí es donde se juega la producción. Si el *correlation engine* central es C++, la ingesta desde fuentes externas (Zeek/Suricata) debe diseñarse bajo las siguientes premisas:

| Componente | Mecanismo de Salida Nativo | Estrategia de Adaptador Recomendada |
| --- | --- | --- |
| **Suricata Adapter** | Unix Socket / Redis (`eve.json` stream) | **C++ Single-Threaded Worker:** Un proceso ligero que lea el socket Unix o consuma de Redis de forma local en la VM y publique en ZeroMQ usando un formato binario compacto (Protobuf). |
| **Zeek Adapter** | Plugins nativos / `conn.log` rotado | **Zeek Plugin (C++) o Streamer externo:** Evitar parsing de texto crudo (`zeek-cut`) en producción. Es preferible un *shipper* mínimo en C++ que consuma la salida de Zeek o un script Zeek que envíe eventos directamente. |

**Dictamen P1:** Mantén el verificador en Python. Para los adaptadores de producción en la VM, **usa C++**. Al mantenerlos alineados con el stack tecnológico de aRGus, evitas introducir el *runtime* de Python en el flujo continuo 24/7 y garantizas que el consumo de CPU de los *shippers* sea despreciable.

---

### P2 — Criterio de Aceptación para el Replay en Vivo

Para el test de mañana (#1 real), un entorno controlado con una tasa baja y sin pérdida de paquetes (*no-drop*), **no podemos ser tibios**. El criterio de aceptación para dar el "Verde" operativo debe ser estricto pero segmentado.

Proponemos la siguiente política de triaje automática en el verificador:

* **Fallo Inmediato (Bloqueante):** Cualquier discrepancia en flujos **TCP establecidos estándar (con SYN/ACK limpios) o UDP simples**. Si aquí hay una anomalía, es un bug de canonicalización en nuestra implementación o en la ordenación de las tuplas. Tolerancia: **0%**.
* **Anomalías Tolerables (Bajo Lupa):** Flujos huérfanos (paquetes sueltos sin *handshake* donde Suricata o Zeek no logren inicializar el estado del flujo de la misma forma que aRGus) o flujos que crucen la barrera del tiempo de inactivación (*timeout*).
* **Plan de Acción:** El script de mañana debe fallar (exit 1) si hay una sola anomalía en la categoría bloqueante. Las anomalías tolerables se registrarán en `cid-xcheck-anomalies.tsv` y se considerarán un "Paso con Advertencia" que alimentará el refinamiento de los *timeouts*.

---

### P3 — Invariante de Promiscuidad en VirtualBox

Confirmado al cien por cien. El comportamiento de *unknown-unicast* en las redes internas (`intnet`) de VirtualBox es una fuente clásica de falsos positivos en entornos de pruebas. Si los adaptadores no están configurados explícitamente para inundar el tráfico promiscuo, el tráfico se aislará por dirección MAC y los sensores quedarán ciegos de forma selectiva.

Debes asegurar este invariante directamente en el `Vagrantfile`. Asumiendo que `eth1` corresponde a la segunda interfaz de red (`nic2`), inyecta la directiva de personalización para cada una de las tres VMs (Suricata, Zeek, Defender):

```ruby
config.vm.provider "virtualbox" do |v|
  # Asegurar que eth1 capture TODO el tráfico de la red interna intnet
  v.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
end

```

*Nota: Si tu mapeo de interfaces desplaza eth1 a otra posición (ej. nic3), ajusta el índice numérico del comando en consecuencia.*

---

## 2. Plan para Mañana (DAY 172)

1. **Hardening del Vagrantfile:** Añadir el flag `--nicpromisc2 allow-all` y hacer un `vagrant reload`.
2. **Lanzamiento del Replay en Vivo (#1):** Ejecutar `tcpreplay` a velocidad controlada.
3. **Extracción de Métricas de Tiempo:** Analizar el Delta de los timestamps de emisión (`ts_emision_ns`) recolectados hoy para empezar a mapear empíricamente la diferencia de comportamiento entre el procesado casi real de aRGus y el cierre por timeout de los otros dos sensores.

El cimiento del data-plane está casi listo para el asalto final. El Consejo queda a la espera de los resultados del replay real.

---

Considerando que mañana analizarás la diferencia de tiempo en la emisión de los IDs (`ts_emision_ns`) entre los tres sensores debido a sus políticas de *timeout*, ¿tienes previsto inyectar tráfico con ráfagas de inactividad artificiales en el pcap para forzar el vaciado (*flush*) de flujos de Suricata y Zeek, o te basarás exclusivamente en la distribución temporal natural que ya viene grabada en los datos de Neris?

FIRMADO
GEMINI