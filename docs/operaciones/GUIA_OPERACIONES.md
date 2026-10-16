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
   - Síntoma: `sniffer.log` dice `[DDOS-ARRANQUE] AVISO agregador del kernel desactivado`.
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

---

## DDOS-ARRANQUE

Líneas de `sniffer.log` sobre el arranque de la cabeza DDoS.

- `[DDOS-ARRANQUE] primera foto del agregador a X ms del arranque (Y ventanas ...); eventos sellados FRIO sin foto: N`.
  Informativa, una por arranque. X es lo que tarda el agregador del kernel en dar su primera tasa (en el
  laboratorio, ~1,0 s). Durante ese tiempo la cabeza DDoS no puede ver un ataque: es la ceguera física de
  arranque, que ninguna configuración elimina. N cuenta los eventos del sniffer de ese intervalo, fast alerts
  incluidas (a 300 pps, unos 2 por paquete). Si X se acerca a `ddos_victim_arranque_ventanas` ×
  `ddos_kernel_agg_interval_ms`, subir `ddos_victim_arranque_ventanas`.
- `[DDOS-ARRANQUE] AVISO agregador del kernel desactivado ...`. La configuración apaga el agregador: ver
  DDOS-V2-ANOMALIA, punto 1.
- `[DDOS-ARRANQUE] ERROR sin foto del agregador tras el plazo de arranque ...`. Ver DDOS-V2-ANOMALIA, punto 4.

---

## DDOS-ESTADO

El sniffer guarda el estado de cada víctima de la cabeza DDoS (su tráfico de base, cuántas ventanas lleva
vista y si está bajo presión) en `ddos_victim_estado_ruta` (por defecto
`/var/lib/argus/sniffer/ddos_victim_estado.csv`): cada `ddos_victim_estado_volcado_ventanas` ventanas y
al parar. Al arrancar lo restaura, para que un reinicio en mitad de un ataque no lo olvide. Sin ese
estado, todas las víctimas arrancan en frío y un ataque por debajo de `ddos_victim_ewma_abs_pps` se
aprendería como tráfico normal.

Líneas de `sniffer.log`:

- `[DDOS-ESTADO] restauradas N víctimas (M bajo presión) ..., volcado de hace X s`: normal.
- `[DDOS-ESTADO] sin estado previo ...`: normal en la primera ejecución. Si aparece en un reinicio
  normal, el volcado no está funcionando: buscar el AVISO de volcado.
- `[DDOS-ESTADO] primer volcado: ...` y `volcado de parada: ...`: normales.
- `[DDOS-ESTADO] AVISO no se pudo volcar ...`: se repite en cada intento fallido. Causas: permisos o disco
  lleno en el directorio de `ddos_victim_estado_ruta`. Corregirlo; el sniffer sigue protegiendo, pero un
  reinicio dejaría las víctimas en frío.
- `[DDOS-ESTADO] AVISO estado previo descartado (motivo)`: el sniffer arranca en frío. Según el motivo:
  - `caducado`: el sniffer estuvo parado más de `ddos_victim_estado_max_edad_ventanas`. Normal tras una
    parada larga.
  - `fecha del volcado en el futuro`: el reloj de la máquina va atrasado. Revisar la sincronización
    horaria (chrony; en el laboratorio, `make lab-clock-step`).
  - `interval_ms del volcado distinto del actual`: se cambió `ddos_kernel_agg_interval_ms`. Esperado una
    vez tras el cambio.
  - `cabecera desconocida`, `columnas desconocidas`, `fila N mal formada`, `filas leídas distintas`: el
    fichero está dañado o lo ha modificado alguien. **Guardar una copia para investigarlo** y abrir
    incidencia: un fichero manipulado podría intentar cegar la detección (la firma del fichero está
    pendiente, DEBT-DDOS-STATE-HMAC-001). El sniffer ya lo ha descartado y sigue en frío.

El fichero queda con permisos 600 (solo su dueño lo lee y escribe).
