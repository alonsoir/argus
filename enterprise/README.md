# aRGus NDR — Enterprise Plugins

## Principio rector

**Fail-closed, never fail-open.**

Si el token enterprise es incorrecto, está expirado, o no existe, el sistema
se detiene completamente con un mensaje claro. No hay fallback silencioso a
la versión OSS. Activar OSS o Enterprise es una decisión explícita del admin.

## Decisión de configuración

El admin debe elegir explícitamente en `argus.conf`:

```ini
# Opción A — OSS explícito
crypto_provider = seed_file

# Opción B — Enterprise explícito
crypto_provider = vault
enterprise_token_path = /etc/argus/enterprise.token
```

Si `crypto_provider` no está configurado → el sistema se para.
Si `crypto_provider = vault` y el token falla validación → el sistema se para.
No existe ninguna tercera opción implícita.

## Plugins enterprise disponibles

| Plugin | Directorio | Estado | Features requeridas |
|--------|-----------|--------|---------------------|
| Cifrado/Compresión via Vault | `plugins/vault_crypto/` | WIP Day 160 | `vault_crypto` |
| Generación de datasets | `plugins/dataset_generator/` | BACKLOG | `dataset_generator` |
| Ensemble ML plugins | `plugins/ensemble_builder/` | BACKLOG | `ensemble_builder` |
| Grafos Neo4j | `plugins/graph_engine/` | BACKLOG | `graph_engine` |
| Integración Wazuh | `plugins/wazuh_integration/` | BACKLOG | `wazuh_integration` |
| Integración Suricata/Zeek | `plugins/suricata_zeek/` | BACKLOG | `suricata_zeek` |
| Dashboards | `plugins/dashboards/` | BACKLOG | `dashboards` |

## Qué NO es enterprise

- El core C++20 del pipeline (sniffer, ml-detector, etcd-server, firewall-acl-agent)
- El plugin OSS de cifrado/compresión con seed_file (`crypto-transport/`)
- El plugin-loader en sí mismo
- Las librerías comunes (`common/`, `contrib/`)

## Generación de tokens

Ver `scripts/generate_token.py`. Requiere la clave privada Ed25519 del operador.
Los tokens se generan **offline** — no hay servidor de licencias.
Esto es una decisión deliberada para entornos críticos sin internet fiable.

## Validación de tokens

`token/TokenValidator.hpp` — header-only, sin dependencias externas salvo libsodium.
Se integra en `plugin-loader/` antes de cualquier `dlopen()` enterprise.
