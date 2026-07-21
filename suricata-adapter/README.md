# suricata-adapter

Adapter del contrato bronce `correlation_v1` para **suricata**.

Traduce la salida nativa del sensor a filas del bronce (19 columnas) y las serializa
con `libs/correlation-v1`. **No reimplementa el contrato**: `validate()` y el HMAC
viven en la librería, que es el notario único (P3).

## Corte en tres capas

| Capa | Quién | Dónde |
|---|---|---|
| nativo → `Row` | este componente | `src/to_row.cpp` |
| `Row` → bytes | `libs/correlation-v1` | `serialize()` |
| bytes → disco | este componente | `src/batch_writer.cpp` |

`to_row` es **pura**: sin fichero, sin reloj, sin red. Todo el I/O vive en
`main.cpp` y `batch_writer.cpp`. Por eso el test no necesita montar nada.

## Uso

```sh
export ARGUS_BRONZE_HMAC_KEY_HEX=<64 chars hex>
suricata_adapter config/suricata_adapter.json [entrada.json]
```

Escribe `<base_dir>/suricata-%Y-%m-%d-%H%M%S.csv` de forma atómica (`.tmp` → rename).
Sale con código 1 si no escribió ninguna fila: cero filas es un fallo, no un éxito
silencioso.

## Invariantes que este componente NO puede romper

- **Nunca reimplementar `validate()`, el HMAC ni el formato CSV.** Si hiciera falta
  cambiar los bytes, se cambia la librería y se enteran los cinco productores.
- **Descarte explícito y ruidoso** (D5). Un `Skip` silencioso es indistinguible de
  un bug; por eso `Skip` lleva motivo y `main` imprime los contadores.
- **`node_id` es el punto de observación** (D2), no el host. Viene de la config.
- **Los 3 scores quedan a `0.0`** = ausencia documentada (D6). El consumidor filtra
  por `source_sensor`.

## Deudas conocidas que le afectan

- `DEBT-SNIFFER-IP-BYTE-ORDER-001` — hasta que se arregle, el `community_id` de
  aRGus está corrupto y **estas filas no convergen con las suyas** aunque ambas
  sean correctas por separado.
- Guard **D-D** diferido: cuando se active, `"suricata"` tendrá que ser un símbolo
  `DetectorSource` legal o `validate()` empezará a rechazar estas filas.

## Estándar

Este layout es el estándar de todos los adapters. El de aRGus vive hoy incrustado
en `ml-detector/src/correlation_writer.cpp` (`to_correlation_v1_row`) y debe salir
de ahí, en su propia refactorización, para cumplirlo. Generado con:

```sh
python3 tools/scaffold_adapter.py --sensor suricata
```
