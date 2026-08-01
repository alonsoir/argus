# wazuh-adapter

Adapter del contrato bronce `host_domain_v1` para **wazuh** (dominio HOST, no red).

Traduce las alertas del manager (`alerts.json`, JSON por línea) a filas del bronce host
(34 columnas) y las serializa con `libs/host-domain-v1`. **No reimplementa el contrato**:
`validate()`, el HMAC, `mint_event_id()` y `encode_string_list()` viven en la librería, que
es el notario único (P3).

> **Wazuh = host-domain, NO red.** Este bronce va a su **buzón propio**
> (`/vagrant/logs/host-domain`) y, aguas abajo, a su **propia BD Kuzu** —
> NUNCA al `$KUZU` de red compartido. Contrato `host_domain_v1`, separado de
> `correlation_v1`.

## Corte en tres capas

| Capa | Quién | Dónde |
|---|---|---|
| `alerts.json` → `Row` | este componente | `src/to_row.cpp` |
| `Row` → bytes | `libs/host-domain-v1` | `serialize()` |
| bytes → disco | este componente | `src/batch_writer.cpp` |

`to_row` es **pura**: sin fichero, sin reloj, sin red. Todo el I/O vive en `main.cpp` y
`batch_writer.cpp`.

## Uso

```sh
export ARGUS_BRONZE_HMAC_KEY_HEX=<64 chars hex>
wazuh_adapter config/wazuh_adapter.json [alerts.json]
```

Escribe `<base_dir>/wazuh-%Y-%m-%d-%H%M%S.csv` de forma atómica (`.tmp` → rename). Sale con
código 1 si no escribió ninguna fila (cero filas es un fallo, no un éxito silencioso).

## Mapeo (medido sobre el snapshot day240)

- **event_id** (col 2): acuñado por `mint_event_id()` sobre la línea **cruda** (idempotencia
  por fichero). El `id` crudo de Wazuh (`epoch.offset`) se guarda como procedencia en
  `wazuh_alert_id` (col 4), nunca como PK.
- **host_id** (col 3) = `agent.id` (PK del nodo Host). Si viene vacío, `validate()` **rechaza**
  la fila; el adapter no duplica esa política.
- **data_json** (col 17) = volcado compacto del bag `data` con **orden de claves preservado**;
  las comunes (`srcuser`/`dstuser`/`srcip`/`srcport`/`uid`/`command`) se extraen aparte
  (`""` = ausente). MITRE y cumplimiento se capturan como listas JSON-celda.
- **saneado de saltos de línea** (D-HOST-3): `full_log`/`rule_description`/`command` pueden traer
  `\n`/`\r` reales (medido: `rule.id 533` netstat es multilínea). Se convierten a escape literal
  para que **1 fila lógica = 1 línea física** — el evento sobrevive en vez de que `validate()` lo
  rechace.

## Invariantes que este componente NO puede romper

- **Nunca reimplementar `validate()`, el HMAC, el `event_id` ni el formato CSV.** Si hiciera
  falta cambiar los bytes, se cambia la librería.
- **Descarte explícito y ruidoso** (D5): hoy sólo la línea vacía es `Skip`; JSON ilegible es
  `Error`; `main` imprime los contadores.
- **Bronce y para.** El `bronze→oro→Kuzu` es aguas abajo (piezas posteriores), como en
  suricata/zeek.

## Deudas conocidas que le afectan

- `DEBT-HOST-DOMAIN-P2` — `alerts.json` es LIVE y rota; el watermark por `(inode, offset)` es
  pieza posterior. Hoy se lee el fichero fresco entero (camino reproducible del paper:
  `destroy&up`).
- `DEBT-HOST-DOMAIN-P1` — FIM/SCA/rootcheck no aparecen en el arranque; se provocan con técnica
  MITRE host-touching en `mitre-start` (paso 3). Sin eso, el grafo host muestra higiene de auth,
  no "Wazuh cazó el ataque".

## Estándar

Mismo layout que suricata/zeek-adapter. A diferencia de ellos, host **no tiene oráculo previo**:
la definición del contrato es `libs/host-domain-v1` (`host_domain_v1_ref.py` como golden).