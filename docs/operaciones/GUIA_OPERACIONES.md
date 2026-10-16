# Guía de operaciones de aRGus NDR

Para el administrador de una instalación. Cada aviso que aRGus escribe en sus logs para el
administrador tiene aquí una sección con el mismo nombre: qué significa, qué impacto tiene,
cómo se diagnostica y qué hacer. Si un aviso de los logs no está en esta guía, es un fallo de la
guía: abrir una incidencia.

Convenciones:
- `[ETIQUETA]` al principio de la línea del log es el nombre de la sección.
- Las rutas de ejemplo son las del laboratorio (`/vagrant/...`). En una instalación real, las del
  despliegue.
- Ningún aviso de esta guía detiene el pipeline: aRGus sigue protegiendo con lo que funciona
  mientras el administrador actúa.

---

## DDOS-V2-ANOMALIA

### El mensaje

En `ml-detector.log`, cada 10 s mientras dure:

    [DDOS-V2-ANOMALIA] estado_victima_ausente=N en los últimos 10 s: eventos sin victim_state ...

### Qué significa

La cabeza DDoS recibe del sniffer, en cada evento, el estado de la víctima (frío, normal, bajo
presión). Ese estado lo calcula el agregador por víctima del kernel. N eventos llegaron **sin**
ese estado.

### Impacto

**La cabeza DDoS no puede marcar ataques en esos eventos.** Si el aviso es continuo, la
instalación está sin detección DDoS. El resto del pipeline sigue funcionando.

No es normal en ningún arranque. Durante los primeros segundos (el plazo de arranque,
`ddos_victim_arranque_ventanas`) el sniffer marca las víctimas como frías y este aviso no salta.

### Diagnóstico y acción, en orden

Primero, buscar en `sniffer.log` las líneas `[DDOS-ARRANQUE]`, `[DDOS-HYST]` y `[WARNING]` del
último arranque.

1. **Agregador apagado en la configuración.**
   - Síntoma: no hay ninguna línea `[DDOS-ARRANQUE]`.
   - Comprobar: `kernel_space.ddos_kernel_agg_enabled` en `sniffer.json`.
   - Acción: ponerlo a `true` y reiniciar el sniffer.
2. **Objeto eBPF sin el mapa del agregador.**
   - Síntoma: `sniffer.log` dice que el mapa no está disponible ("objeto eBPF anterior al
     parche; lector DDoS desactivado").
   - Acción: el binario y el objeto eBPF no son de la misma versión. Reinstalar la versión
     completa del pipeline (en el laboratorio, `make pipeline-build PROFILE=production`) y
     reiniciar.
3. **El lector del agregador no arrancó.**
   - Síntoma: `[WARNING] no se pudo arrancar el lector DDoS; sigo sin el`.
   - Causa habitual: no se puede abrir el fichero `ddos_kernel_agg_csv_path` (permisos, disco
     lleno, directorio inexistente).
   - Acción: corregirlo, o dejar la ruta vacía si no se necesita el CSV, y reiniciar el sniffer.
4. **El lector arrancó pero no entregó ninguna foto en el plazo.**
   - Síntoma: `[DDOS-ARRANQUE] ERROR sin foto del agregador tras el plazo de arranque`.
   - Si la máquina va muy cargada al arrancar, el plazo puede quedarse corto. Comparar con la
     línea `[DDOS-ARRANQUE] primera foto ... a X ms` de arranques anteriores. Si X se acerca al
     plazo, subir `ddos_victim_arranque_ventanas` en `sniffer.json` (rango 2-60).
   - Si no hay foto nunca: el lector está bloqueado. Reiniciar el sniffer y, si se repite, abrir
     incidencia con el `sniffer.log` completo.
5. **Sniffer de versión anterior al ml-detector.**
   - Síntoma: no hay ningún problema en `sniffer.log`, pero el aviso sigue.
   - Causa: el sniffer no envía el campo `victim_state` (versión anterior a DAY298).
   - Acción: desplegar sniffer y ml-detector de la misma versión.

### Cuándo deja de ser urgente

Si aparece una sola vez justo después de un arranque, con N pequeño, y no se repite, el plazo
de arranque es algo corto para esa máquina. No hay pérdida sostenida de detección. Aplicar el
punto 4 con calma.

### Referencias

DEBT-DDOS-ESTADO-ARRANQUE-001 (docs/BACKLOG.md); docs/ml-heads/day298_etapa1_resultados.md.
