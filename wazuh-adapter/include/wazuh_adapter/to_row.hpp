// wazuh-adapter/include/wazuh_adapter/to_row.hpp
// aRGus NDR — alerts.json (Wazuh) -> HostDomainV1Row. Capa PURA del adapter.
//
// A diferencia de suricata/zeek, host NO tiene oráculo previo: la DEFINICIÓN del
// contrato es libs/host-domain-v1 (host_domain_v1_ref.py como golden). Este to_row
// aplana la línea JSON del manager a las 34 columnas y ACUÑA el event_id llamando a
// host_domain_v1::mint_event_id() sobre la línea CRUDA (idempotencia por fichero).
//
// PURA: sin fichero, sin reloj, sin red, sin fetch de clave. El test le pasa una línea
// literal y comprueba el Row campo a campo sin montar nada. VERIFICADO DAY 242: C++ y la
// referencia Python cruzan byte-idéntico sobre las 6 líneas reales del snapshot day240.
#pragma once

#include <string>

#include <host_domain_v1/host_domain_v1.hpp>

namespace wazuh_adapter {

// D-C (host_domain_v1.hpp): schema_version y source_sensor son CAMPOS del Row, no
// constantes de la librería. Este adapter los fija. (En host, schema_version = el
// NOMBRE del contrato, no un ordinal — congelado en los vectores de Pieza 0.)
inline constexpr const char* SCHEMA_VERSION = "host_domain_v1";   // col 0
inline constexpr const char* SOURCE_SENSOR  = "wazuh";            // col 1

// ---------------------------------------------------------------------------
// Resultado de tres estados (D5, descarte explícito). IMITA el ToRowResult de
// suricata/zeek para que el mecanismo sea el mismo en los cuatro productores.
//   Ok    -> hay fila (host_id vacío NO lo filtra aquí: lo rechaza serialize()/validate,
//            notario único — el adapter no duplica la política del contrato).
//   Skip  -> descarte legítimo con motivo (hoy: solo la línea vacía).
//   Error -> bug del productor (JSON ilegible). Ruidoso.
// ---------------------------------------------------------------------------
struct [[nodiscard]] ToRowResult {
    enum class Status { Ok, Skip, Error };

    Status status = Status::Error;
    host_domain_v1::HostDomainV1Row row{};
    std::string reason;   // motivo del Skip o diagnóstico del Error; vacío si Ok

    static ToRowResult ok(host_domain_v1::HostDomainV1Row r);
    static ToRowResult skip(std::string why);
    static ToRowResult error(std::string what);
};

// ---------------------------------------------------------------------------
// to_row — una línea de alerts.json -> HostDomainV1Row.
// raw_line: los bytes EXACTOS de la línea (getline, sin el \n). Se usan tal cual para
// mint_event_id (col 2) ANTES de parsear -> idempotencia por fichero.
// ---------------------------------------------------------------------------
[[nodiscard]] ToRowResult to_row(const std::string& raw_line);

}  // namespace wazuh_adapter