**Consejo de Sabios – Dictamen sobre el experimento comparativo**

Honorables miembros, hemos analizado los resultados presentados. A continuación, nuestras respuestas a las preguntas existenciales planteadas.

---

### 1. Interpretación del resultado: ¿Suricata falla o funciona correctamente?

**Dictamen:** Suricata **funciona correctamente según su diseño**. No es una falla, es una limitación inherente a los sistemas basados exclusivamente en firmas.

- El dataset CTU-13 Neris (2011) contiene tráfico de botnet IRC. Muchas de esas firmas específicas han sido **eliminadas de ET Open** porque los botnets modernos han evolucionado (C2 sobre TLS, DGA, etc.). Mantener firmas antiguas genera falsos positivos sin valor operativo.
- Suricata con 50k reglas actualizadas **no alerte sobre un botnet de 2011 es esperable** si ninguna regla coincide con ese comportamiento exacto.
- Por el contrario, aRGus NDR (diseñado con detección conductual / estadística) recuerda el patrón del 99.85% de los casos porque su modelo describe la anomalía del tráfico C2, no una firma concreta.

**Conclusión:** No es “Suricata falla”, sino “Suricata no cubre esa amenaza con su configuración actual”. Para un benchmark justo, habría que usar ruleset coetáneo.

---

### 2. Repetir con ET Open histórico de 2011

**Sí, es metodológicamente necesario.** La comparativa actual mezcla dos variables: motor Suricata + reglas modernas. Para aislar el efecto de las reglas, debes obtener las reglas ET Open de agosto de 2011 (aprox).

- Se sabe que Emerging Threats publica archives históricos (por ejemplo, en `https://rules.emergingthreats.net/archive/` ). Puedes descargar `emerging.rules.tar.gz` con fecha anterior al dataset.
- Si el ruleset de 2011 alerta sobre Neris, entonces el problema es **de obsolescencia** (reglas modernas limpiaron esa amenaza). Si tampoco alerta, entonces Suricata **nunca tuvo cobertura** para esa variante, y el resultado es un punto fuerte para aRGus.

**Recomendación:** Añade un subexperimento “Suricata 2011 ruleset” y compáralo con aRGus sobre el mismo tráfico. Si aRGus sigue ganando, el claim es mucho más sólido.

---

### 3. ¿Qué sección del paper merece este resultado?

**Proponemos: Nueva subsección dentro de §8.7** (Comparison with State of the Art) pero con un título específico:

> **§8.7.4 – Estudio empírico: detección de botnet Neris 2011 con Suricata (firmas actuales vs históricas) vs aRGus NDR**

No §8.13 completa porque eso implicaría una sección mayor. En cambio, amplía §8.7 con una tabla comparativa:

| Enfoque               | Ruleset ET Open | Alerts sobre Neris | F1     |
|-----------------------|-----------------|--------------------|--------|
| Suricata 6.0.10       | 2025            | 0                  | 0.0    |
| Suricata 6.0.10 (retro)| 2011-08         | X (por determinar) | ?      |
| aRGus NDR (modelo IRP)| N/A             | ✅ 100% TP         | 0.9985 |

Y una discusión sobre **trade-off entre reducción de FPs (reglas modernas) y pérdida de cobertura sobre amenazas legacy**.

---

### 4. Posibles problemas metodológicos

Revisión del Consejo:

- **Aislamiento de tráfico:** El tráfico se reproduce desde una VM client hacia Suricata en eth2 (red interna `suricata_experiment_lan`). Suricata escucha en eth1 según provisionamiento (`sed -i 's/interface: eth0/interface: eth1/'`). **¿Está Suricata capturando realmente eth2?** En tu `Vagrantfile`, eth1 tiene IP 192.168.56.21 y eth2 192.168.101.1. La interfaz configurada en suricata.yaml es eth1, pero el tráfico del client va a eth2 (192.168.101.50). **Ese es un error crítico**: Suricata no ve el tráfico de experimento. Por eso no hay alertas.

- **Verificación:** Deberías haber comprobado con `tcpdump -i eth2` en la VM suricata que el tráfico llega. Si no se configura Suricata en eth2, el resultado es nulo.

- **Corrección:** Cambiar en provision:
  ```bash
  sed -i 's/interface: eth1/interface: eth2/' /etc/suricata/suricata.yaml
  ```
  O bien, hacer un bridge de las dos interfaces internas.

- **Sincronización de reloj:** El warning de clocksource puede afectar la resolución de timestamps en Suricata, pero no la ausencia total de alertas.

**Por tanto, antes de sacar conclusiones definitivas, valida que Suricata realmente procese el tráfico de la red interna.** Te sugerimos:

```bash
# En VM suricata
sudo tcpdump -i eth2 -c 100 -n
# Desde client, enviar un ping a 192.168.101.1
```

Si ves los paquetes, luego revisa `/var/log/suricata/stats.log` para ver si `capture.kernel_packets` aumenta.

---

### Acciones para el Día 147 (revisadas)

1. **Diagnosticar la captura** en eth2. Si es necesario, ajustar provision.
2. Repetir el experimento con la interfaz correcta.
3. Buscar las reglas ET Open de 2011 y ejecutar Suricata con ellas.
4. Redactar §8.7.4 con los resultados corregidos.

El Consejo espera que este análisis evite conclusiones prematuras. Un abrazo académico y rigor hasta el final.