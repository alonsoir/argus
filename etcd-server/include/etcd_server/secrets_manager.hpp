#pragma once
// etcd-server/include/etcd_server/secrets_manager.hpp — [ETCD-CLAVES-D314]
// Claves HMAC del bronce con ventana de dos, persistidas en un ISecretStore (Vault en la VM etcd; memoria en el defender
// hasta el paso 6). DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.4. Sustituye al SecretsManager de DAY54 (claves solo en memoria:
// un reinicio del etcd-server daba otra clave y el bronce anterior ya no se podía verificar; carrera de DAY311 en
// leer-o-crear; enfriamiento sin mutex; parse_time con mktime).
//
// En el almacén (rutas relativas al montaje; el CN ya validado por la tabla authz):
//   <CN>/<huella8> = {"clave": hex, "creada": ISO-8601 UTC}       inmutable: se escribe con CAS 0 y nunca se borra
//   <CN>/ventana   = {"activa": h8, "anterior": h8|"", "expira_anterior": ISO|""}   se cambia con CAS = versión leída
// huella8 = 4 primeros bytes del SHA-256 de los bytes de la clave, en hex (igual que CorrelationWriter::fingerprint
// del ml-detector). En el log solo sale la huella, nunca la clave.
//
// Reglas (decisiones de Alonso DAY310/DAY313/DAY314):
//   - Un único mutex para leer-o-crear y rotar: dos primeras peticiones no crean dos claves. Entre procesos (PR2, HA)
//     lo garantiza el CAS: si otro creó o rotó antes, se relee y se usa lo suyo.
//   - Almacén no disponible: se sirve la última ventana conocida (desde_copia = true); sin copia, NoDisponible (503) y
//     NUNCA se genera una clave que no quede guardada. Rotar exige el almacén (503).
//   - Enfriamiento: no se rota sin force antes de min_rotation_interval_seconds desde que se creó la clave activa
//     (medido en el almacén: vale tras un reinicio y entre instancias). Como min_rotation >= grace, la anterior ya
//     caducó cuando llega la siguiente rotación: nunca hay más de dos claves válidas.
//   - Avisos periódicos: [ETCD-CLAVES-MEMORIA] (modo memoria) y [ETCD-VAULT-NO-DISPONIBLE] cada aviso_intervalo_s;
//     [ETCD-VAULT-RECUPERADO] al volver.
#include "etcd_server/etcd_server_claves.hpp"
#include <atomic>
#include <ctime>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace etcd_server {

struct SecretsConfig {
    int grace_period_seconds = 300;
    int default_key_length_bytes = 32;
    int min_rotation_interval_seconds = 300;
};

struct ClaveHMAC {
    std::string hex;           // la clave (hex): SOLO para la respuesta HTTP al componente autorizado
    std::string huella;        // 8 hex
    std::time_t creada = 0;
    std::time_t expira = 0;    // 0 = activa (no caduca)
    bool activa = false;
};

enum class ResultadoClaves { Ok, NoDisponible, Enfriamiento, Conflicto, NombreInvalido };

class SecretsManager {
public:
    using Reloj = std::function<std::time_t()>;
    using Generador = std::function<std::string(size_t bytes)>;  // devuelve hex

    SecretsManager(const SecretsConfig& cfg, std::unique_ptr<argus::claves::ISecretStore> almacen, bool modo_memoria,
                   int aviso_intervalo_s, int sondeo_s, Reloj reloj = [] { return std::time(nullptr); },
                   std::ostream& log = std::cout, Generador generador = {});
    ~SecretsManager();
    SecretsManager(const SecretsManager&) = delete;
    SecretsManager& operator=(const SecretsManager&) = delete;

    // GET /secrets/{c}: la activa; si no hay ninguna (y el almacén responde), la crea
    ResultadoClaves activa(const std::string& cn, ClaveHMAC& out, bool& desde_copia);
    // POST /secrets/rotate/{c}: reintentar_s se rellena con Enfriamiento
    ResultadoClaves rotar(const std::string& cn, bool force, ClaveHMAC& nueva, int& reintentar_s);
    // GET /secrets/valid/{c}: activa + anterior si no ha caducado (activa primero). Sin clave todavía: Ok y vacío
    ResultadoClaves validas(const std::string& cn, std::vector<ClaveHMAC>& out, bool& desde_copia);

    // Arranque: un sondeo del almacén con su línea de log ([ETCD-VAULT] conectado | [ETCD-VAULT-NO-DISPONIBLE])
    void comprobar_al_arrancar();
    // Una pasada de avisos periódicos y sondeo si está caído (pública para los tests; el monitor la llama cada 1 s)
    void revisar();
    void arrancar_monitor();
    void parar_monitor();

    bool almacen_disponible();
    int get_grace_period_seconds() const { return cfg_.grace_period_seconds; }

    static std::string huella(const std::string& hex);
    static std::string iso(std::time_t t);
    static bool desde_iso(const std::string& s, std::time_t& t);

private:
    struct Ventana {
        std::string activa, anterior;
        std::time_t expira_anterior = 0;
        int version = 0;
    };
    using Estado = argus::claves::Estado;

    Estado leer_ventana_locked(const std::string& cn, Ventana& v, bool permitir_copia, bool& desde_copia);
    Estado leer_clave_locked(const std::string& cn, const std::string& h, ClaveHMAC& out);
    Estado crear_clave_locked(const std::string& cn, ClaveHMAC& out);
    Estado anotar(Estado e);
    std::string generar(size_t bytes);

    SecretsConfig cfg_;
    std::unique_ptr<argus::claves::ISecretStore> almacen_;
    const bool modo_memoria_;
    const int aviso_, sondeo_;
    Reloj reloj_;
    std::ostream& log_;
    Generador generador_;

    std::mutex m_;
    std::map<std::string, Ventana> ventanas_;   // última ventana conocida por CN (la copia)
    std::map<std::string, ClaveHMAC> claves_;   // "<CN>/<huella>" -> clave (inmutables: se guardan para siempre)
    bool disponible_ = true;
    std::time_t caida_desde_ = 0, ultimo_aviso_caida_ = 0, ultimo_aviso_memoria_ = 0, ultimo_sondeo_ = 0;
    bool aviso_memoria_dado_ = false;

    std::atomic<bool> monitor_activo_{false};
    std::thread monitor_;
};

}  // namespace etcd_server
