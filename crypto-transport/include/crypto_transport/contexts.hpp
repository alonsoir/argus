#pragma once

// =============================================================================
// ML Defender — HKDF Context Constants
// crypto-transport/include/crypto_transport/contexts.hpp
//
// REGLA: el contexto pertenece al CANAL, no al componente.
// Emisor y receptor del mismo canal usan la misma constante
// → misma clave derivada → sin MAC error.
//
// ADR-013 PHASE 2 — DAY 99
// =============================================================================

namespace ml_defender::crypto {

// Canal: sniffer → ml-detector
constexpr const char* CTX_SNIFFER_TO_ML     = "ml-defender:sniffer-to-ml-detector:v1";

// Canal: ml-detector → firewall-acl-agent
constexpr const char* CTX_ML_TO_FIREWALL    = "ml-defender:ml-detector-to-firewall:v1";

// Canal: etcd (bidireccional, tx/rx desde perspectiva del cliente)
constexpr const char* CTX_ETCD_TX           = "ml-defender:etcd:v1:tx";
constexpr const char* CTX_ETCD_RX           = "ml-defender:etcd:v1:rx";

// Canal: ml-detector / firewall → rag-ingester (artefactos RAG)
constexpr const char* CTX_RAG_ARTIFACTS     = "ml-defender:rag-artifacts:v1";

} // namespace ml_defender::crypto
