#pragma once
#include <stdint.h>  /* uint8_t, uint16_t, uint32_t */
#include <stddef.h>  /* size_t */
// ============================================================================
// plugin_api.h — ML Defender Plugin Contract (C ABI)
// ============================================================================
// API C pura para máxima portabilidad y ABI stability entre compilaciones.
// Todo plugin DEBE exportar los 6 símbolos definidos al final de este header.
//
// Restricciones PHASE 1 (ADR-012):
//   - Plugins: SOLO feature extraction
//   - Decisión de bloqueo: NUNCA en un plugin
//   - Crash isolation (proceso separado + watchdog): PHASE 2
//   - Autenticación de plugins: PHASE 2 (seed-client, DAY 95-96)
//
// Versionado: si se modifica esta API, incrementar PLUGIN_API_VERSION.
// El loader rechaza plugins con versión distinta (warning, no abort).
// ============================================================================

#ifdef __cplusplus
extern "C" {
#endif

#define PLUGIN_API_VERSION 1

// ----------------------------------------------------------------------------
// PluginConfig — pasado a plugin_init()
// ----------------------------------------------------------------------------
typedef struct PluginConfig {
    const char* name;         // nombre del plugin (ej: "hello", "ja4")
    const char* config_json;  // sección JSON del plugin como string (puede ser "{}")
} PluginConfig;

// ----------------------------------------------------------------------------
// PacketContext — contexto por paquete, pasado a plugin_process_packet()
// El plugin PUEDE escribir en threat_hint.
// El plugin NO debe castear features ni alert_queue sin conocer la versión del host.
// ----------------------------------------------------------------------------
typedef struct PacketContext {
    // Read-only: datos del flujo
    const uint8_t* raw_bytes;
    size_t         length;
    uint32_t       src_ip;
    uint32_t       dst_ip;
    uint16_t       src_port;
    uint16_t       dst_port;
    uint8_t        protocol;

    // Write: enriquecimiento de features (puntero opaco al FlowFeatures del host)
    void*          features;

    // Write: cola de alertas del componente host (puntero opaco)
    void*          alert_queue;

    // Write: sugerencia de amenaza del plugin
    //   0 = benign, 1 = suspicious, 2 = malicious
    // La DECISIÓN FINAL de bloqueo pertenece siempre al core (ADR-012).
    int            threat_hint;
} PacketContext;


// ----------------------------------------------------------------------------
// PluginMode — modo de invocación del plugin (Q1 Consejo DAY 109)
// PLUGIN_MODE_NORMAL:   payload presente, D8-v2 CRC32 activo (sniffer, PHASE 2c)
// PLUGIN_MODE_READONLY: payload=nullptr garantizado (rag-ingester, PHASE 2b)
// El loader valida coherencia pre-invocación (D8):
//   PLUGIN_MODE_READONLY && (payload!=nullptr || payload_len!=0) → std::terminate()
// ----------------------------------------------------------------------------
typedef enum {
    PLUGIN_MODE_NORMAL   = 0,  // acceso normal al payload
    PLUGIN_MODE_READONLY = 1   // rag-ingester: payload=nullptr garantizado
} PluginMode;

// ----------------------------------------------------------------------------
// MessageContext — contexto por mensaje ZMQ, pasado a plugin_process_message()
// ADR-023 PHASE 2a — Integración firewall-acl-agent
//
// Trust model (D7): plugins son código de terceros — tratados como UNTRUSTED.
//   El loader valida invariantes post-invocación (D8).
//   La decisión de bloqueo pertenece SIEMPRE al core (ADR-012).
//
// TCB (D9): solo PluginLoader + CryptoTransport pertenecen al TCB.
//   El plugin NO tiene acceso a claves ni a CryptoTransport interno.
//
// Forward-compatibility (D11): reserved[60] reservado para ADR-024
//   (Dynamic Group Key Agreement — campos a definir en FASE 3).
// ----------------------------------------------------------------------------
typedef struct MessageContext {
    // Read-only: payload post-decrypt + post-decompress (D2)
    // Ownership: el host retiene el buffer. El plugin NO debe liberar ni retener.
    // Lifetime:  válido SOLO durante la llamada a plugin_process_message().
    const uint8_t* payload;
    size_t         payload_len;

    // Read-only: metadatos de flujo (D2)
    uint32_t       src_ip;
    uint32_t       dst_ip;
    uint16_t       src_port;
    uint16_t       dst_port;
    uint8_t        protocol;

    // Read-only: dirección de transporte (D3)
    // 0 = RX (entrante desde ml-detector), 1 = TX (saliente)
    // El plugin NUNCA debe modificar este campo.
    uint8_t        direction;

    // Read-only: metadatos crypto (D3)
    // nonce y tag son propiedad del CryptoTransport.
    // El plugin puede inspeccionarlos pero NUNCA modificarlos ni liberarlos.
    //
    // nonce: 12-byte ChaCha20 nonce (contador monotónico 96-bit, ADR-017).
    // tag:   16-byte Poly1305 MAC tag.
    //
    // Production guarantee: nonce != NULL && tag != NULL.
    // Test/config mode (--test-config, MLD_DEV_MODE): MAY be NULL.
    // Plugins MUST check for NULL before dereferencing.
    const uint8_t* nonce;   // 12 bytes — contador monotónico 96-bit (ADR-017)
    const uint8_t* tag;     // 16 bytes — MAC Poly1305

    // Write: salida del plugin
    // result_code: 0 = OK, !=0 = plugin señaliza anomalía
    //   NOTA: result_code != 0 NO bloquea por sí solo — el core decide.
    int            result_code;
    // annotation: anotacion opcional null-terminated (max 63 chars + null)
    char           annotation[64];
    // mode: PluginMode — consume 1 byte de reserved (Q1 Consejo DAY 109)
    // El loader valida coherencia pre-invocación (D8):
    //   PLUGIN_MODE_READONLY && (payload!=nullptr || payload_len!=0) → std::terminate()
    uint8_t        mode;          // PluginMode — ver enum arriba
    // Reservado: forward-compatibility ADR-024 (D11)
    uint8_t        reserved[59];  // era [60] — 1 byte consumido por mode
} MessageContext;

// ----------------------------------------------------------------------------
// PluginResult — código de retorno de las funciones del plugin
// ----------------------------------------------------------------------------
typedef enum {
    PLUGIN_OK    = 0,  // operación correcta
    PLUGIN_ERROR = 1,  // error — el loader incrementa error counter
    PLUGIN_SKIP  = 2   // plugin decide no procesar este paquete/evento
} PluginResult;

// ----------------------------------------------------------------------------
// Símbolos OBLIGATORIOS que todo plugin debe exportar
// ----------------------------------------------------------------------------

// Identificación
const char*  plugin_name();           // ej: "hello"
const char*  plugin_version();        // ej: "0.1.0"
int          plugin_api_version();    // debe retornar PLUGIN_API_VERSION

// Ciclo de vida
PluginResult plugin_init(const PluginConfig* config);
PluginResult plugin_process_packet(PacketContext* ctx);
void         plugin_shutdown();

// ----------------------------------------------------------------------------
// Símbolo OPCIONAL — plugin_process_message() (ADR-023 PHASE 2a)
// ----------------------------------------------------------------------------
// Si el plugin no exporta este símbolo, el loader aplica Graceful Degradation
// Policy D1: skip silencioso en producción.
// Si PLUGIN_API_VERSION se incrementa en el futuro, este símbolo se volverá
// obligatorio — documentado en ADR-023 D11.
// La DECISIÓN FINAL de bloqueo pertenece siempre al core (ADR-012).
// ----------------------------------------------------------------------------
PluginResult plugin_process_message(MessageContext* ctx);


#ifdef __cplusplus
}
#endif
