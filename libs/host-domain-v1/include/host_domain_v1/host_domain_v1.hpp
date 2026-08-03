// host_domain_v1.hpp
// aRGus NDR — libhost_domain_v1: serialización PURA del contrato bronce host_domain_v1
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// PROCEDENCIA (DAY 241): a diferencia de libcorrelation_v1 (que EXTRAJO su capa de
// serialización de un oráculo previo, ml-detector/correlation_writer.cpp), aquí NO hay
// oráculo. aRGus no produce filas de host; la ÚNICA fuente es el alerts.json de Wazuh.
// Por eso ESTA LIB ES LA DEFINICIÓN PRIMARIA del contrato host_domain_v1: el golden se
// caracteriza contra una REFERENCIA PYTHON escrita a tal efecto, no contra un binario C++.
// CERO protobuf · CERO red · CERO I/O de fichero · CERO fetch de clave.
//
// CORTE EN TRES CAPAS (la struct es la frontera donde el JSON de Wazuh muere):
//   [alerts.json -> Row]  wazuh-adapter (Pieza 1, EXCLUSIVO) — parsea la línea JSON,
//                         aplana a columnas, y ACUÑA event_id llamando a mint_event_id()
//                         de ESTA lib sobre la línea cruda. Solo el adapter habla JSON.
//   [Row -> bytes]        serialize()  — ESTA LIB. Notario único de los bytes (P3):
//                         el wazuh-adapter embuda aquí, igual que suricata/zeek embudan
//                         en correlation_v1::serialize.
//   [bytes -> disco]      batch_writer del adapter — rotación + ofstream + reloj.
//
// CONTRATO host_domain_v1 — 34 columnas (0-32 datos, 33 HMAC-SHA256 sobre cols 0-32):
//    0 schema_version    1 source_sensor     2 event_id          3 host_id
//    4 wazuh_alert_id    5 timestamp         6 agent_id          7 agent_name
//    8 agent_ip          9 os_hostname      10 rule_id          11 rule_level
//   12 rule_description 13 rule_groups[json] 14 decoder_name    15 location
//   16 full_log         17 data_json[json]  18 srcuser          19 dstuser
//   20 srcip            21 srcport          22 uid              23 command
//   24 mitre_ids[json]  25 mitre_tactics[json]  26 mitre_techniques[json]
//   27 pci_dss[json]    28 gdpr[json]       29 hipaa[json]      30 nist_800_53[json]
//   31 tsc[json]        32 gpg13[json]      33 HMAC-SHA256 (sobre cols 0-32)
//
// DECISIONES CONGELADAS (DAY 241):
//   D-A   Error como valor TIPADO, nunca excepción ni línea silenciosa. [[nodiscard]]
//         sobre el TIPO (idéntico a correlation_v1): el fallo de validez no se descarta
//         bajo -Werror.
//   D-C   schema_version / source_sensor son CAMPOS del Row, no constantes. El adapter de
//         Wazuh los fija a "host_domain_v1" / "wazuh". La lib no los conoce.
//   D-E   imbue(std::locale::classic()) en CADA stream, dentro de la lib. Hallazgo P0 de
//         correlation_v1 heredado: bajo es_ES los enteros saldrían con separador de
//         millares y los bytes se romperían. Defensa en profundidad, no se confía en el
//         locale ambiental. (rule_level es el único entero del contrato host; el hallazgo
//         aplica igual.)
//
//   D-HOST-1  DOS PRIMITIVAS, no una (correlation_v1 solo tenía serialize). El event_id
//         se ACUÑA aquí, no llega hecho de aguas arriba:
//           event_id = "wz1:" + base64_std( BLAKE2b-256( TAG || raw_line ) )
//           TAG = "argus-hostevent-v1"   raw_line = bytes EXACTOS de la línea JSON
//                                                    ANTES de parsear (da idempotencia
//                                                    por fichero).
//         Mismo linaje que flow_uid (tag de versión + BLAKE2b-256 + base64), namespaced
//         con "wz1:" para que sea visiblemente distinto del espacio de event_id de red.
//         El id crudo de Wazuh (epoch.offset) se conserva en la col 4 (wazuh_alert_id)
//         como PROCEDENCIA, nunca como PK. El sello (col 33) es HMAC-SHA256 con la clave
//         COMPARTIDA con la red (ARGUS_BRONZE_HMAC_KEY_HEX) — decisión por sencillez, el
//         ledger/loader host son par separado y cualquier clave sella igual.
//
//   D-HOST-2  LISTAS EN JSON-CELDA. Diez campos del contrato son listas (rule_groups,
//         mitre_ids/tactics/techniques, y las seis de cumplimiento pci_dss..gpg13). Un CSV
//         plano no las mete en una celda; se codifican como JSON compacto canónico vía
//         encode_string_list() — el MISMO mecanismo que data_json ya obliga a tener, cero
//         convención nueva. Al llegar al Row esos campos YA son std::string con JSON, así
//         que el Row es todo escalar y serialize() es casi verbatim del de red.
//         Se CAPTURAN en el bronce, NO se reconstruyen desde rule_id: Vía Appia exige que
//         el grafo sea reconstruible DESDE EL LEDGER SOLO. El mapeo MITRE/cumplimiento es
//         fehaciente respecto a la VERSIÓN del ruleset del manager; el ledger registra lo
//         que Wazuh dijo EN EL MOMENTO, robusto al drift del ruleset.
//
//   D-HOST-3  ERROR FUNDAMENTAL = host_id vacío. Sustituye al guard "community_id vacío"
//         de correlation_v1 (host no tiene community_id). host_id (= agent.id) es la PK del
//         nodo Host; sin él no hay a quién colgar el evento -> validate RECHAZA, va primero.
//         El barrido de \n/\r embebido sobre campos de texto libre se hereda 1:1 de
//         correlation_v1 (DEBT-BRONZE-EMBEDDED-NEWLINE-001): 1 fila lógica = 1 línea física.
//         AVISO: en host este guard SÍ dispara de verdad (full_log / data_json /
//         rule_description salen de logs) — el adapter debe mantener esos campos
//         JSON-escapados o validate los rechaza (correctamente). \t NO se rechaza.
//
//   D-HOST-4  TIPOS: rule_level es int32 y es el ÚNICO entero. Está SIEMPRE presente (una
//         alerta sin regla no es una alerta); si faltara, es input malformado -> validate
//         RECHAZA, NO se le pone un sentinel (un sentinel diría "ausente pero válido", y
//         aquí ausente = no es alerta). Los comunes extraídos del bag data (srcport, uid,
//         srcuser, dstuser, srcip, command) son STRING: en data faltan a menudo (solo
//         sshd trae srcport, solo PAM trae uid) y "" = ausente de forma natural, sin
//         reservar valor mágico. NO se usa sentinel numérico (p.ej. 9999 sería un uid real
//         de Linux -> colisión con dato legítimo, justo lo que un sentinel no puede
//         permitirse). rule_id es STRING: identidad tipo-PK (D4 del contrato), no cantidad.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace host_domain_v1 {

inline constexpr size_t TOTAL_COLS = 34;   // 0-32 datos + 33 HMAC

// ----------------------------------------------------------------------------
// HostDomainV1Row — la fila que emite el wazuh-adapter. Datos cols 0-32.
// La col 33 (HMAC-SHA256 sobre 0-32) la calcula serialize(); no se almacena aquí.
//
// Convención de nombres (para el mantenedor): si el nombre de columna coincide con una
// clave de Wazuh (aplanando el punto a guion bajo: rule.id -> rule_id, decoder.name ->
// decoder_name, data.srcip -> srcip), el dato es DE WAZUH. Si no coincide, es NUESTRO:
//   - event_id (D-HOST-1, acuñado)      - host_id (= agent.id, papel en el grafo)
//   - schema_version / source_sensor (D-C)   - hmac_row (sello, col 33)
// Los campos marcados [json] llegan al Row ya codificados como JSON compacto canónico
// (data_json = bag data completo; el resto vía encode_string_list). D-HOST-2.
// ----------------------------------------------------------------------------
struct HostDomainV1Row {
    // -- producidos por nosotros --
    std::string schema_version;        // 0   (D-C) = "host_domain_v1"
    std::string source_sensor;         // 1   (D-C) = "wazuh"
    std::string event_id;              // 2   (D-HOST-1) acuñado por mint_event_id()
    std::string host_id;               // 3   = agent.id  (PK del nodo Host; error fundamental si vacío)
    // -- copiados de Wazuh --
    std::string wazuh_alert_id;        // 4   = id crudo (epoch.offset), PROCEDENCIA, no PK
    std::string timestamp;             // 5   ISO8601 top-level (millis + TZ)
    std::string agent_id;              // 6
    std::string agent_name;            // 7   = WAZUH_AGENT_NAME (identidad elegida)
    std::string agent_ip;              // 8   vacío si agente 000 (manager)
    std::string os_hostname;           // 9   = predecoder.hostname (hostname real del SO)
    std::string rule_id;               // 10  identidad tipo-PK (D-HOST-4), string
    int32_t     rule_level = 0;        // 11  ÚNICO entero; siempre presente (D-HOST-4)
    std::string rule_description;      // 12
    std::string rule_groups;           // 13  [json] lista
    std::string decoder_name;          // 14
    std::string location;              // 15
    std::string full_log;              // 16  texto libre, gordo (dispara el newline-guard)
    std::string data_json;             // 17  [json] bag data completo (fidelidad)
    // -- comunes extraídas del bag data (string; "" = ausente, D-HOST-4) --
    std::string srcuser;               // 18
    std::string dstuser;               // 19
    std::string srcip;                 // 20  breadcrumb de movimiento lateral (se queda en BD host)
    std::string srcport;               // 21
    std::string uid;                   // 22
    std::string command;               // 23
    // -- MITRE ATT&CK, normalizado por regla aguas abajo (D-HOST-2) --
    std::string mitre_ids;             // 24  [json] lista
    std::string mitre_tactics;         // 25  [json] lista
    std::string mitre_techniques;      // 26  [json] lista
    // -- cumplimiento, capturado aunque los nodos Control sean P4 diferido (D-HOST-2) --
    std::string pci_dss;               // 27  [json] lista
    std::string gdpr;                  // 28  [json] lista
    std::string hipaa;                 // 29  [json] lista
    std::string nist_800_53;           // 30  [json] lista
    std::string tsc;                   // 31  [json] lista
    std::string gpg13;                 // 32  [json] lista
};

// ----------------------------------------------------------------------------
// Resultados tipados (D-A). [[nodiscard]] sobre el TIPO: ni el adapter ni ningún
// productor futuro puede descartar el fallo bajo -Werror.
// ----------------------------------------------------------------------------
struct [[nodiscard]] ValidationResult {
    bool ok = false;
    std::string error;                 // diagnóstico ruidoso si !ok; vacío si ok
    explicit operator bool() const noexcept { return ok; }
};

struct [[nodiscard]] SerializeResult {
    bool ok = false;
    std::string line;                  // cols 0-33 listas para append; vacío si !ok
    std::string error;                 // diagnóstico ruidoso si !ok; vacío si ok
    explicit operator bool() const noexcept { return ok; }
};

// ----------------------------------------------------------------------------
// mint_event_id — PRIMITIVA de identidad (D-HOST-1). Acuña el event_id (col 2) desde la
// línea JSON CRUDA de alerts.json (los bytes exactos, antes de parsear).
//   event_id = "wz1:" + base64_std( BLAKE2b-256( "argus-hostevent-v1" || raw_line ) )
// PURA y determinista. BLAKE2b-256 SIN clave (libsodium crypto_generichash, digest 32),
// tag de dominio como prefijo del mensaje — mismo patrón que flow_uid.
// Golden: hashlib.blake2b(TAG + raw_line, digest_size=32).digest() -> base64.b64encode.
// ----------------------------------------------------------------------------
[[nodiscard]] std::string mint_event_id(const std::string& raw_line);

// ----------------------------------------------------------------------------
// encode_string_list — PRIMITIVA de codificación de listas (D-HOST-2). vector -> JSON
// compacto canónico para meter una lista en una celda del CSV bronce.
//   ["a","b"]  con separadores (',',':'), sin espacios, orden PRESERVADO tal como lo
//   emite Wazuh (no se ordena). Lista vacía -> "[]".
// PURA y determinista. Tiene su PROPIO vector congelado (golden aparte de serialize).
// Golden: json.dumps(items, separators=(',',':'), ensure_ascii=False).
// ----------------------------------------------------------------------------
[[nodiscard]] std::string encode_string_list(const std::vector<std::string>& items);

// ----------------------------------------------------------------------------
// validate — NOTARIO ÚNICO del contrato (P3). Invariantes ESTRUCTURALES que TODO
// productor del dominio host debe cumplir, independientes de quién construyó el Row.
//   - ERROR FUNDAMENTAL (va primero): host_id vacío = sin nodo Host al que colgar el
//     evento (D-HOST-3).
//   - Newline-guard: \n/\r embebido en cualquier campo de texto libre rompe el reader
//     getline (1 fila lógica != 1 línea física; DEBT-BRONZE-EMBEDDED-NEWLINE-001,
//     heredado de correlation_v1). \t NO se rechaza.
// ----------------------------------------------------------------------------
[[nodiscard]] ValidationResult validate(const HostDomainV1Row& row) noexcept;

// ----------------------------------------------------------------------------
// serialize — Row -> línea bronce completa (cols 0-33 incl. HMAC-SHA256 sobre 0-32).
//
// PURA: función de (row, hmac_key) y NADA más.
//   · sin reloj            (timestamp es dato del Row; ingested_at no vive aquí)
//   · sin locale ambiental (imbue classic interno — D-E)
//   · sin red, sin fichero
//   · sin fetch de clave   (hmac_key es INPUT — el caller la trae de donde sea:
//                           ARGUS_BRONZE_HMAC_KEY_HEX, compartida con la red, D-HOST-1)
//
// Llama a validate() primero (P3): un Row que validate rechaza, serialize NO lo emite.
// NO acuña event_id: espera que el adapter ya haya fijado row.event_id vía mint_event_id.
// hmac_key: 32 bytes (decodificados de los 64 hex chars por el caller).
// ----------------------------------------------------------------------------
[[nodiscard]] SerializeResult serialize(const HostDomainV1Row& row,
                                        const std::vector<uint8_t>& hmac_key);

} // namespace host_domain_v1