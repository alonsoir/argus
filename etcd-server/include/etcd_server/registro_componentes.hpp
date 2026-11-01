#pragma once
// etcd-server/include/etcd_server/registro_componentes.hpp — [ETCD-REGISTRO-D313]
// Registro de componentes sobre IRegistryStore (DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.3). Sustituye al unordered_map sin
// mutex de ComponentRegistry. Decisiones de Alonso (DAY313):
//   - Claves (mismo comportamiento que hoy): registro/<CN> = el documento único del componente (lo escriben /register y
//     PUT /v1/config; el último gana; GET /config lo devuelve), latido/<CN> = {"ultimo", "estado"}, epoca.
//   - Muerto = se MARCA, no se borra: el monitor pone estado "muerto" ([ETCD-COMPONENTE-MUERTO]) y el siguiente latido
//     lo revive ([ETCD-COMPONENTE-REVIVIDO]) y da 200. Antes se desregistraba y sus latidos daban 404 para siempre.
//   - Almacén no disponible: las lecturas salen de la última copia en memoria; las escrituras devuelven NoDisponible
//     (503) y el log avisa [ETCD-ALMACEN-NO-DISPONIBLE] cada aviso_intervalo_s. etcd es la única verdad (HA del PR2):
//     no se acepta nada solo en memoria. Al volver: [ETCD-ALMACEN-RECUPERADO] y se recarga la copia.
//   - Un único mutex para la copia y el estado (antes components_ se tocaba sin mutex desde HTTP y desde el monitor).
// Sin dependencias de etcd ni de la criptografía: se prueba suelto con MemoriaRegistryStore y un reloj inyectado.
#include "etcd_server/etcd_server_almacen.hpp"
#include "etcd_server/etcd_server_authz.hpp"
#include <nlohmann/json.hpp>
#include <atomic>
#include <chrono>
#include <ctime>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace argus::registro {

using argus::almacen::Estado;
using argus::almacen::IRegistryStore;

enum class Resultado { Ok, NoEncontrado, NoDisponible, NombreInvalido, DocumentoInvalido };

class RegistroComponentes {
public:
    using Reloj = std::function<std::time_t()>;

    RegistroComponentes(std::unique_ptr<IRegistryStore> almacen, int latido_intervalo_s, int latido_multiplicador,
                        int revision_intervalo_s, int aviso_intervalo_s, bool modo_memoria,
                        Reloj reloj = [] { return std::time(nullptr); }, std::ostream& log = std::cout)
        : almacen_(std::move(almacen)),
          intervalo_(latido_intervalo_s),
          multiplicador_(latido_multiplicador),
          revision_(revision_intervalo_s),
          aviso_(aviso_intervalo_s),
          modo_memoria_(modo_memoria),
          reloj_(std::move(reloj)),
          log_(log) {
        std::lock_guard<std::mutex> lk(m_);
        log_ << "[ETCD-REGISTRO] almacén: " << almacen_->descripcion() << "; muerto tras "
             << (intervalo_ * multiplicador_) << " s sin latido (se marca, no se borra); revisión cada " << revision_
             << " s" << std::endl;
        cargar_locked();
    }

    ~RegistroComponentes() { parar_monitor(); }
    RegistroComponentes(const RegistroComponentes&) = delete;
    RegistroComponentes& operator=(const RegistroComponentes&) = delete;

    void arrancar_monitor() {
        if (monitor_activo_.exchange(true)) return;
        monitor_ = std::thread([this] {
            while (monitor_activo_) {
                // a trozos de 100 ms: la parada no espera a revision_intervalo_s (antes, hasta 10 s)
                for (int i = 0; i < revision_ * 10 && monitor_activo_; ++i)
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                if (monitor_activo_) revisar_latidos();
            }
        });
    }
    void parar_monitor() {
        if (!monitor_activo_.exchange(false)) return;
        if (monitor_.joinable()) monitor_.join();
    }

    static bool nombre_valido(const std::string& n) { return argus::etcdauthz::nombre_valido(n); }

    // /register y PUT /v1/config: documento único; latido "activo" ahora
    Resultado registrar(const std::string& nombre, const nlohmann::json& doc_in) {
        if (!nombre_valido(nombre)) return Resultado::NombreInvalido;
        if (!doc_valido(doc_in)) return Resultado::DocumentoInvalido;
        nlohmann::json doc = doc_in;
        if (!doc.contains("component")) doc["component"] = nombre;
        if (!doc.contains("version")) doc["version"] = "1.0";
        std::lock_guard<std::mutex> lk(m_);
        const auto t = reloj_();
        Estado e = anotar(almacen_->poner("registro/" + nombre, doc.dump()));
        if (e == Estado::NoDisponible) return Resultado::NoDisponible;
        const nlohmann::json lat = {{"ultimo", t}, {"estado", "activo"}};
        e = anotar(almacen_->poner("latido/" + nombre, lat.dump()));
        if (e == Estado::NoDisponible) return Resultado::NoDisponible;
        docs_[nombre] = doc;
        latidos_[nombre] = lat;
        log_ << "[ETCD-REGISTRO] registrado " << nombre << std::endl;
        return Resultado::Ok;
    }

    Resultado desregistrar(const std::string& nombre) {
        if (!nombre_valido(nombre)) return Resultado::NombreInvalido;
        std::lock_guard<std::mutex> lk(m_);
        std::string v;
        Estado e = anotar(almacen_->leer("registro/" + nombre, v));
        if (e == Estado::NoDisponible) return Resultado::NoDisponible;
        if (e == Estado::NoEncontrado) {
            docs_.erase(nombre);
            latidos_.erase(nombre);
            return Resultado::NoEncontrado;
        }
        if (anotar(almacen_->borrar("registro/" + nombre)) == Estado::NoDisponible) return Resultado::NoDisponible;
        if (anotar(almacen_->borrar("latido/" + nombre)) == Estado::NoDisponible) return Resultado::NoDisponible;
        docs_.erase(nombre);
        latidos_.erase(nombre);
        log_ << "[ETCD-REGISTRO] desregistrado " << nombre << std::endl;
        return Resultado::Ok;
    }

    // PUT /config/{c}: doc[path] = value (como hoy: campo de primer nivel)
    Resultado actualizar_campo(const std::string& nombre, const std::string& path, const std::string& value) {
        if (!nombre_valido(nombre)) return Resultado::NombreInvalido;
        std::lock_guard<std::mutex> lk(m_);
        nlohmann::json doc;
        const Resultado r = leer_locked(nombre, doc, /*permitir_cache=*/false);
        if (r != Resultado::Ok) return r;
        doc[path] = value;
        if (anotar(almacen_->poner("registro/" + nombre, doc.dump())) == Estado::NoDisponible)
            return Resultado::NoDisponible;
        docs_[nombre] = doc;
        return Resultado::Ok;
    }

    // GET /config/{c}: de etcd; si no está disponible, de la copia en memoria
    Resultado leer_documento(const std::string& nombre, nlohmann::json& out) {
        if (!nombre_valido(nombre)) return Resultado::NombreInvalido;
        std::lock_guard<std::mutex> lk(m_);
        return leer_locked(nombre, out, /*permitir_cache=*/true);
    }

    // POST /v1/heartbeat/{c}: NoEncontrado si no está registrado (404); revive si estaba muerto
    Resultado latir(const std::string& nombre, std::time_t& ultimo) {
        if (!nombre_valido(nombre)) return Resultado::NombreInvalido;
        std::lock_guard<std::mutex> lk(m_);
        std::string v;
        Estado e = anotar(almacen_->leer("registro/" + nombre, v));
        if (e == Estado::NoDisponible) return Resultado::NoDisponible;
        if (e == Estado::NoEncontrado) return Resultado::NoEncontrado;
        std::string previo = "activo";
        std::time_t previo_t = 0;
        if (anotar(almacen_->leer("latido/" + nombre, v)) == Estado::Ok) {
            try {
                const auto j = nlohmann::json::parse(v);
                previo = j.value("estado", "activo");
                previo_t = j.value("ultimo", static_cast<std::time_t>(0));
            } catch (...) {
            }
        }
        const auto t = reloj_();
        const nlohmann::json lat = {{"ultimo", t}, {"estado", "activo"}};
        if (anotar(almacen_->poner("latido/" + nombre, lat.dump())) == Estado::NoDisponible)
            return Resultado::NoDisponible;
        latidos_[nombre] = lat;
        if (previo == "muerto") {
            log_ << "[ETCD-COMPONENTE-REVIVIDO] " << nombre << " vuelve a latir tras " << (t - previo_t)
                 << " s sin latido" << std::endl;
        }
        ultimo = t;
        return Resultado::Ok;
    }

    // GET /components: de etcd; si no está disponible, de la copia (desde_copia = true)
    Resultado listar(std::vector<std::string>& out, bool& desde_copia) {
        std::lock_guard<std::mutex> lk(m_);
        out.clear();
        std::map<std::string, std::string> m;
        if (anotar(almacen_->listar("registro/", m)) == Estado::Ok) {
            desde_copia = false;
            for (const auto& [k, _] : m) out.push_back(k.substr(std::string("registro/").size()));
            return Resultado::Ok;
        }
        desde_copia = true;
        for (const auto& [k, _] : docs_) out.push_back(k);
        return Resultado::Ok;
    }

    size_t cuenta() {
        std::vector<std::string> v;
        bool c = false;
        listar(v, c);
        return v.size();
    }

    // "activo" | "muerto" | "" (sin latido); para la línea del monitor y los tests
    std::string estado_latido(const std::string& nombre) {
        std::lock_guard<std::mutex> lk(m_);
        auto it = latidos_.find(nombre);
        return it == latidos_.end() ? "" : it->second.value("estado", "");
    }

    std::time_t ultimo_latido(const std::string& nombre) {
        std::lock_guard<std::mutex> lk(m_);
        auto it = latidos_.find(nombre);
        return it == latidos_.end() ? 0 : it->second.value("ultimo", static_cast<std::time_t>(0));
    }

    Resultado guardar_epoca(const nlohmann::json& ep) {
        std::lock_guard<std::mutex> lk(m_);
        if (anotar(almacen_->poner("epoca", ep.dump())) == Estado::NoDisponible) return Resultado::NoDisponible;
        epoca_ = ep;
        return Resultado::Ok;
    }
    // NoEncontrado si nunca se guardó (quien llama usa su defecto)
    Resultado leer_epoca(nlohmann::json& ep) {
        std::lock_guard<std::mutex> lk(m_);
        std::string v;
        const Estado e = anotar(almacen_->leer("epoca", v));
        if (e == Estado::Ok) {
            try {
                epoca_ = nlohmann::json::parse(v);
            } catch (...) {
                return Resultado::NoEncontrado;
            }
        } else if (e == Estado::NoEncontrado) {
            return Resultado::NoEncontrado;
        }
        if (epoca_.is_null()) return e == Estado::NoDisponible ? Resultado::NoDisponible : Resultado::NoEncontrado;
        ep = epoca_;
        return Resultado::Ok;
    }

    // Una pasada del monitor (pública para los tests)
    void revisar_latidos() {
        std::lock_guard<std::mutex> lk(m_);
        const auto t = reloj_();
        if (modo_memoria_ && (ultimo_aviso_memoria_ == 0 || t - ultimo_aviso_memoria_ >= aviso_)) {
            log_ << "[ETCD-ALMACEN-MEMORIA] registro solo en memoria (almacen.modo=memoria): se pierde al reiniciar. "
                    "Solo transición hasta el paso 6 de DEBT-ETCD-HA-TLS-RAFT-001"
                 << std::endl;
            ultimo_aviso_memoria_ = t;
        }
        if (recargar_) cargar_locked();
        std::map<std::string, std::string> m;
        if (anotar(almacen_->listar("latido/", m)) != Estado::Ok) {
            aviso_no_disponible_locked(t);
            return;  // sin almacén no se marca nada: lo que se ve en la copia puede estar viejo
        }
        const std::time_t limite = static_cast<std::time_t>(intervalo_) * multiplicador_;
        for (const auto& [k, v] : m) {
            const std::string nombre = k.substr(std::string("latido/").size());
            nlohmann::json j;
            try {
                j = nlohmann::json::parse(v);
            } catch (...) {
                continue;
            }
            latidos_[nombre] = j;
            const std::time_t u = j.value("ultimo", static_cast<std::time_t>(0));
            if (j.value("estado", "") == "activo" && t - u > limite) {
                j["estado"] = "muerto";
                if (anotar(almacen_->poner(k, j.dump())) == Estado::Ok) {
                    latidos_[nombre] = j;
                    log_ << "[ETCD-COMPONENTE-MUERTO] " << nombre << " sin latido hace " << (t - u) << " s (límite "
                         << limite << " s): se marca muerto, el registro se conserva" << std::endl;
                }
            }
        }
        aviso_no_disponible_locked(t);
    }

    bool almacen_disponible() {
        std::lock_guard<std::mutex> lk(m_);
        return disponible_;
    }

private:
    static bool doc_valido(const nlohmann::json& d) {
        if (!d.is_object() || !d.contains("component")) return false;
        const auto& c = d["component"];
        return c.is_string() || (c.is_object() && c.contains("name"));
    }

    Resultado leer_locked(const std::string& nombre, nlohmann::json& out, bool permitir_cache) {
        std::string v;
        const Estado e = anotar(almacen_->leer("registro/" + nombre, v));
        if (e == Estado::Ok) {
            try {
                out = nlohmann::json::parse(v);
            } catch (...) {
                return Resultado::NoEncontrado;
            }
            docs_[nombre] = out;
            return Resultado::Ok;
        }
        if (e == Estado::NoEncontrado) {
            docs_.erase(nombre);
            return Resultado::NoEncontrado;
        }
        if (!permitir_cache) return Resultado::NoDisponible;
        auto it = docs_.find(nombre);
        if (it == docs_.end()) return Resultado::NoDisponible;
        out = it->second;
        return Resultado::Ok;
    }

    void cargar_locked() {
        std::map<std::string, std::string> r, l;
        if (anotar(almacen_->listar("registro/", r)) != Estado::Ok || anotar(almacen_->listar("latido/", l)) != Estado::Ok) {
            log_ << "[ETCD-REGISTRO] no se pudo cargar el registro del almacén: se reintenta en cada revisión"
                 << std::endl;
            recargar_ = true;
            return;
        }
        docs_.clear();
        latidos_.clear();
        for (const auto& [k, v] : r) {
            try {
                docs_[k.substr(std::string("registro/").size())] = nlohmann::json::parse(v);
            } catch (...) {
            }
        }
        for (const auto& [k, v] : l) {
            try {
                latidos_[k.substr(std::string("latido/").size())] = nlohmann::json::parse(v);
            } catch (...) {
            }
        }
        recargar_ = false;
        std::string nombres;
        for (const auto& [n, _] : docs_) {
            if (!nombres.empty()) nombres += ',';
            nombres += n;
        }
        log_ << "[ETCD-REGISTRO-CARGADO] " << docs_.size() << " componentes del almacén"
             << (docs_.empty() ? std::string() : (": " + nombres)) << std::endl;
    }

    // Toda llamada al almacén pasa por aquí: lleva el estado disponible / no disponible y sus avisos
    Estado anotar(Estado e) {
        const auto t = reloj_();
        if (e == Estado::NoDisponible) {
            if (disponible_) {
                disponible_ = false;
                caida_desde_ = t;
                ultimo_aviso_caida_ = t;
                log_ << "[ETCD-ALMACEN-NO-DISPONIBLE] " << almacen_->descripcion() << ": " << almacen_->ultimo_error()
                     << ". Lecturas desde la copia en memoria; escrituras 503" << std::endl;
            }
        } else if (!disponible_) {
            disponible_ = true;
            recargar_ = true;
            log_ << "[ETCD-ALMACEN-RECUPERADO] tras " << (t - caida_desde_) << " s; se recarga la copia" << std::endl;
        }
        return e;
    }

    void aviso_no_disponible_locked(std::time_t t) {
        if (!disponible_ && t - ultimo_aviso_caida_ >= aviso_) {
            log_ << "[ETCD-ALMACEN-NO-DISPONIBLE] sigue sin responder desde hace " << (t - caida_desde_)
                 << " s: escrituras 503, lecturas de la copia" << std::endl;
            ultimo_aviso_caida_ = t;
        }
    }

    std::unique_ptr<IRegistryStore> almacen_;
    const int intervalo_, multiplicador_, revision_, aviso_;
    const bool modo_memoria_;
    Reloj reloj_;
    std::ostream& log_;

    std::mutex m_;
    std::map<std::string, nlohmann::json> docs_;
    std::map<std::string, nlohmann::json> latidos_;
    nlohmann::json epoca_;
    bool disponible_ = true;
    bool recargar_ = false;
    std::time_t caida_desde_ = 0, ultimo_aviso_caida_ = 0, ultimo_aviso_memoria_ = 0;

    std::atomic<bool> monitor_activo_{false};
    std::thread monitor_;
};

}  // namespace argus::registro
