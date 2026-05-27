#include "EtcdServiceRegistry.h"
#include <iostream>
#include <json/json.h>
#include <chrono>
#include <sstream>
#include <algorithm>
#include <cstring>

// Base64 encoding table
static const std::string base64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

// Inicialización de miembros estáticos
std::unique_ptr<EtcdServiceRegistry> EtcdServiceRegistry::instance_ = nullptr;
std::mutex EtcdServiceRegistry::instance_mutex_;

EtcdServiceRegistry::EtcdServiceRegistry(const std::string& etcd_endpoint)
    : running_(false), lease_id_(0) {
    try {
        // Inicializar libcurl
        curl_global_init(CURL_GLOBAL_DEFAULT);
        curl_handle_ = curl_easy_init();

        if (!curl_handle_) {
            throw std::runtime_error("No se pudo inicializar libcurl");
        }

        etcd_base_url_ = etcd_endpoint;
        if (etcd_base_url_.back() == '/') {
            etcd_base_url_.pop_back();
        }

        std::cout << "[EtcdServiceRegistry] Cliente REST conectado a: " << etcd_endpoint << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Error inicializando cliente REST: " << e.what() << std::endl;
        throw;
    }
}

EtcdServiceRegistry::~EtcdServiceRegistry() {
    shutdown();
    if (curl_handle_) {
        curl_easy_cleanup(curl_handle_);
    }
    curl_global_cleanup();
}

EtcdServiceRegistry& EtcdServiceRegistry::getInstance(const std::string& etcd_endpoint) {
    std::lock_guard<std::mutex> lock(instance_mutex_);
    if (instance_ == nullptr) {
        instance_ = std::unique_ptr<EtcdServiceRegistry>(new EtcdServiceRegistry(etcd_endpoint));
    }
    return *instance_;
}

size_t EtcdServiceRegistry::WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

std::string EtcdServiceRegistry::base64Encode(const std::string& input) {
    std::string ret;
    int i = 0;
    int j = 0;
    unsigned char char_array_3[3];
    unsigned char char_array_4[4];

    const char* bytes_to_encode = input.c_str();
    int in_len = input.length();

    while (in_len--) {
        char_array_3[i++] = *(bytes_to_encode++);
        if (i == 3) {
            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
            char_array_4[3] = char_array_3[2] & 0x3f;

            for(i = 0; (i <4) ; i++)
                ret += base64_chars[char_array_4[i]];
            i = 0;
        }
    }

    if (i) {
        for(j = i; j < 3; j++)
            char_array_3[j] = '\0';

        char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
        char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
        char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
        char_array_4[3] = char_array_3[2] & 0x3f;

        for (j = 0; (j < i + 1); j++)
            ret += base64_chars[char_array_4[j]];

        while((i++ < 3))
            ret += '=';
    }

    return ret;
}

bool EtcdServiceRegistry::httpPut(const std::string& key, const std::string& value, int64_t lease_id) {
    try {
        std::string response_string;

        // Preparar JSON para etcd v3 API
        Json::Value request;
        request["key"] = base64Encode(key);
        request["value"] = base64Encode(value);
        if (lease_id > 0) {
            request["lease"] = lease_id;
        }

        Json::StreamWriterBuilder builder;
        std::string json_data = Json::writeString(builder, request);

        std::string url = etcd_base_url_ + "/v3/kv/put";

        curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl_handle_);
        curl_slist_free_all(headers);

        if (res != CURLE_OK) {
            std::cerr << "[EtcdServiceRegistry] Error HTTP: " << curl_easy_strerror(res) << std::endl;
            return false;
        }

        long response_code;
        curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &response_code);

        return response_code == 200;

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Excepción en httpPut: " << e.what() << std::endl;
        return false;
    }
}

std::string EtcdServiceRegistry::httpGet(const std::string& key) {
    try {
        std::string response_string;

        Json::Value request;
        request["key"] = base64Encode(key);

        Json::StreamWriterBuilder builder;
        std::string json_data = Json::writeString(builder, request);

        std::string url = etcd_base_url_ + "/v3/kv/range";

        curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl_handle_);
        curl_slist_free_all(headers);

        if (res != CURLE_OK) {
            return "";
        }

        // Parsear respuesta JSON
        Json::Value response;
        Json::Reader reader;
        if (reader.parse(response_string, response)) {
            if (response["kvs"].isArray() && response["kvs"].size() > 0) {
                std::string encoded_value = response["kvs"][0]["value"].asString();
                return base64Decode(encoded_value);
            }
        }

        return "";

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Error en httpGet: " << e.what() << std::endl;
        return "";
    }
}

std::string EtcdServiceRegistry::base64Decode(const std::string& encoded_string) {
    int in_len = encoded_string.size();
    int i = 0;
    int j = 0;
    int in = 0;
    unsigned char char_array_4[4], char_array_3[3];
    std::string ret;

    while (in_len-- && (encoded_string[in] != '=') &&
           (isalnum(encoded_string[in]) || (encoded_string[in] == '+') || (encoded_string[in] == '/'))) {
        char_array_4[i++] = encoded_string[in]; in++;
        if (i == 4) {
            for (i = 0; i < 4; i++)
                char_array_4[i] = base64_chars.find(char_array_4[i]);

            char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
            char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
            char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

            for (i = 0; (i < 3); i++)
                ret += char_array_3[i];
            i = 0;
        }
    }

    if (i) {
        for (j = i; j < 4; j++)
            char_array_4[j] = 0;

        for (j = 0; j < 4; j++)
            char_array_4[j] = base64_chars.find(char_array_4[j]);

        char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
        char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
        char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

        for (j = 0; (j < i - 1); j++) ret += char_array_3[j];
    }

    return ret;
}

std::vector<std::pair<std::string, std::string>> EtcdServiceRegistry::httpGetWithPrefix(const std::string& prefix) {
    std::vector<std::pair<std::string, std::string>> results;

    try {
        std::string response_string;

        Json::Value request;
        request["key"] = base64Encode(prefix);

        // Para prefix, añadir range_end
        std::string range_end = prefix;
        if (!range_end.empty()) {
            range_end.back()++;
            request["range_end"] = base64Encode(range_end);
        }

        Json::StreamWriterBuilder builder;
        std::string json_data = Json::writeString(builder, request);

        std::string url = etcd_base_url_ + "/v3/kv/range";

        curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl_handle_);
        curl_slist_free_all(headers);

        if (res == CURLE_OK) {
            Json::Value response;
            Json::Reader reader;
            if (reader.parse(response_string, response)) {
                if (response["kvs"].isArray()) {
                    for (const auto& kv : response["kvs"]) {
                        std::string key = base64Decode(kv["key"].asString());
                        std::string value = base64Decode(kv["value"].asString());
                        results.emplace_back(key, value);
                    }
                }
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Error en httpGetWithPrefix: " << e.what() << std::endl;
    }

    return results;
}

int64_t EtcdServiceRegistry::createLease(int64_t ttl) {
    try {
        std::string response_string;

        Json::Value request;
        request["TTL"] = ttl;
        request["ID"] = 0; // Let etcd assign the ID

        Json::StreamWriterBuilder builder;
        std::string json_data = Json::writeString(builder, request);

        std::string url = etcd_base_url_ + "/v3/lease/grant";

        curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl_handle_);
        curl_slist_free_all(headers);

        if (res != CURLE_OK) {
            std::cerr << "[EtcdServiceRegistry] CURL Error: " << curl_easy_strerror(res) << std::endl;
            return 0;
        }

        long response_code;
        curl_easy_getinfo(curl_handle_, CURLINFO_RESPONSE_CODE, &response_code);

        if (response_code == 200) {
            Json::Value response;
            Json::Reader reader;
            if (reader.parse(response_string, response)) {
                if (response.isMember("ID")) {
                    int64_t lease_id = 0;

                    // etcd devuelve el ID como string, no como número
                    if (response["ID"].isString()) {
                        try {
                            lease_id = std::stoll(response["ID"].asString());
                        } catch (const std::exception& e) {
                            std::cerr << "[EtcdServiceRegistry] Error convirtiendo lease ID: " << e.what() << std::endl;
                            return 0;
                        }
                    } else if (response["ID"].isInt64()) {
                        lease_id = response["ID"].asInt64();
                    }

                    if (lease_id > 0) {
                        int64_t ttl_response = 0;
                        if (response.isMember("TTL")) {
                            if (response["TTL"].isString()) {
                                ttl_response = std::stoll(response["TTL"].asString());
                            } else if (response["TTL"].isInt64()) {
                                ttl_response = response["TTL"].asInt64();
                            }
                        }

                        std::cout << "[EtcdServiceRegistry] Lease creado: " << lease_id
                                 << " TTL: " << ttl_response << "s" << std::endl;
                        return lease_id;
                    }
                }
            } else {
                std::cerr << "[EtcdServiceRegistry] Error parsing JSON response: " << reader.getFormattedErrorMessages() << std::endl;
            }
        } else {
            std::cerr << "[EtcdServiceRegistry] HTTP Error " << response_code << ": " << response_string << std::endl;
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Excepción creando lease: " << e.what() << std::endl;
        return 0;
    }
}

bool EtcdServiceRegistry::keepAliveLease(int64_t lease_id) {
    try {
        std::string response_string;

        Json::Value request;
        request["ID"] = lease_id;

        Json::StreamWriterBuilder builder;
        std::string json_data = Json::writeString(builder, request);

        std::string url = etcd_base_url_ + "/v3/lease/keepalive";

        curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl_handle_);
        curl_slist_free_all(headers);

        return res == CURLE_OK;

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Error en keepAlive: " << e.what() << std::endl;
        return false;
    }
}

// Implementación de métodos públicos (idéntica a la versión gRPC)
bool EtcdServiceRegistry::registerService(const std::string& service_name,
                                        const std::string& node_id,
                                        const std::string& json_config,
                                        int heartbeat_ttl) {
    try {
        service_name_ = service_name;
        node_id_ = node_id;

        // 1. Crear lease para heartbeat
        lease_id_ = createLease(heartbeat_ttl);
        if (lease_id_ == 0) {
            std::cerr << "[EtcdServiceRegistry] No se pudo crear lease" << std::endl;
            return false;
        }

        // 2. Registrar configuración del servicio
        std::string config_key = generateConfigKey(service_name, "config");
        if (!httpPut(config_key, json_config, lease_id_)) {
            std::cerr << "[EtcdServiceRegistry] Error registrando configuración" << std::endl;
            return false;
        }

        // 3. Registrar información del nodo con heartbeat
        Json::Value node_info;
        node_info["node_id"] = node_id;
        node_info["service_name"] = service_name;
        node_info["status"] = "active";
        node_info["registered_at"] = static_cast<int64_t>(std::time(nullptr));

        Json::StreamWriterBuilder builder;
        std::string node_info_str = Json::writeString(builder, node_info);

        std::string heartbeat_key = generateHeartbeatKey(service_name);
        if (!httpPut(heartbeat_key, node_info_str, lease_id_)) {
            std::cerr << "[EtcdServiceRegistry] Error registrando heartbeat" << std::endl;
            return false;
        }

        // 4. Iniciar hilo de heartbeat
        running_ = true;
        heartbeat_thread_ = std::thread(&EtcdServiceRegistry::heartbeatLoop, this);

        std::cout << "[EtcdServiceRegistry] Servicio '" << service_name
                  << "' registrado exitosamente con lease_id: " << lease_id_ << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Excepción en registerService: " << e.what() << std::endl;
        return false;
    }
}

bool EtcdServiceRegistry::registerServiceWithMultipleConfigs(const std::string& service_name,
                                                           const std::string& node_id,
                                                           const std::map<std::string, std::string>& json_configs,
                                                           int heartbeat_ttl) {
    try {
        service_name_ = service_name;
        node_id_ = node_id;

        lease_id_ = createLease(heartbeat_ttl);
        if (lease_id_ == 0) {
            return false;
        }

        for (const auto& [config_key, json_config] : json_configs) {
            std::string full_key = generateConfigKey(service_name, config_key);
            if (!httpPut(full_key, json_config, lease_id_)) {
                std::cerr << "[EtcdServiceRegistry] Error registrando config '" << config_key << "'" << std::endl;
                return false;
            }
            std::cout << "[EtcdServiceRegistry] Config '" << config_key << "' registrada" << std::endl;
        }

        Json::Value node_info;
        node_info["node_id"] = node_id;
        node_info["service_name"] = service_name;
        node_info["status"] = "active";
        node_info["registered_at"] = static_cast<int64_t>(std::time(nullptr));
        node_info["config_count"] = static_cast<int>(json_configs.size());

        Json::StreamWriterBuilder builder;
        std::string node_info_str = Json::writeString(builder, node_info);

        std::string heartbeat_key = generateHeartbeatKey(service_name);
        if (!httpPut(heartbeat_key, node_info_str, lease_id_)) {
            return false;
        }

        running_ = true;
        heartbeat_thread_ = std::thread(&EtcdServiceRegistry::heartbeatLoop, this);

        std::cout << "[EtcdServiceRegistry] Servicio '" << service_name
                  << "' registrado con " << json_configs.size() << " configuraciones" << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "[EtcdServiceRegistry] Excepción en registerServiceWithMultipleConfigs: " << e.what() << std::endl;
        return false;
    }
}

std::string EtcdServiceRegistry::getServiceConfig(const std::string& service_name, const std::string& config_key) {
    std::string key = generateConfigKey(service_name, config_key);
    return httpGet(key);
}

std::vector<std::string> EtcdServiceRegistry::listServices() {
    std::vector<std::string> services;

    auto results = httpGetWithPrefix("/services/heartbeat/");

    for (const auto& [key, value] : results) {
        // Extraer nombre del servicio de la clave
        size_t last_slash = key.find_last_of('/');
        if (last_slash != std::string::npos) {
            services.push_back(key.substr(last_slash + 1));
        }
    }

    return services;
}

bool EtcdServiceRegistry::isServiceActive(const std::string& service_name) {
    std::string key = generateHeartbeatKey(service_name);
    std::string value = httpGet(key);
    return !value.empty();
}

bool EtcdServiceRegistry::updateServiceConfig(const std::string& service_name,
                                            const std::string& json_config,
                                            const std::string& config_key) {
    std::string key = generateConfigKey(service_name, config_key);
    if (httpPut(key, json_config)) {
        std::cout << "[EtcdServiceRegistry] Config '" << config_key
                 << "' actualizada para servicio '" << service_name << "'" << std::endl;
        return true;
    }
    return false;
}

std::string EtcdServiceRegistry::getServiceHealth(const std::string& service_name) {
    std::string key = generateHeartbeatKey(service_name);
    return httpGet(key);
}

void EtcdServiceRegistry::shutdown() {
    running_ = false;

    if (heartbeat_thread_.joinable()) {
        heartbeat_thread_.join();
    }

    if (lease_id_ > 0) {
        try {
            std::string response_string;

            Json::Value request;
            request["ID"] = lease_id_;

            Json::StreamWriterBuilder builder;
            std::string json_data = Json::writeString(builder, request);

            std::string url = etcd_base_url_ + "/v3/lease/revoke";

            curl_easy_setopt(curl_handle_, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl_handle_, CURLOPT_POSTFIELDS, json_data.c_str());
            curl_easy_setopt(curl_handle_, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl_handle_, CURLOPT_WRITEDATA, &response_string);

            struct curl_slist* headers = nullptr;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl_handle_, CURLOPT_HTTPHEADER, headers);

            CURLcode res = curl_easy_perform(curl_handle_);
            curl_slist_free_all(headers);

            if (res == CURLE_OK) {
                std::cout << "[EtcdServiceRegistry] Lease revocado: " << lease_id_ << std::endl;
            } else {
                std::cerr << "[EtcdServiceRegistry] Error revocando lease: " << curl_easy_strerror(res) << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "[EtcdServiceRegistry] Error en shutdown: " << e.what() << std::endl;
        }
    }
}

void EtcdServiceRegistry::heartbeatLoop() {
    while (running_) {
        try {
            // Mantener el lease vivo
            if (lease_id_ > 0) {
                keepAliveLease(lease_id_);
            }

            // Actualizar timestamp del heartbeat
            Json::Value heartbeat;
            heartbeat["node_id"] = node_id_;
            heartbeat["service_name"] = service_name_;
            heartbeat["status"] = "active";
            heartbeat["last_heartbeat"] = static_cast<int64_t>(std::time(nullptr));

            Json::StreamWriterBuilder builder;
            std::string heartbeat_str = Json::writeString(builder, heartbeat);

            std::string key = generateHeartbeatKey(service_name_);
            httpPut(key, heartbeat_str, lease_id_);

            // Esperar 10 segundos antes del próximo heartbeat
            std::this_thread::sleep_for(std::chrono::seconds(10));

        } catch (const std::exception& e) {
            std::cerr << "[EtcdServiceRegistry] Error en heartbeat: " << e.what() << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }
}

std::string EtcdServiceRegistry::generateServiceKey(const std::string& service_name, const std::string& suffix) {
    std::string key = "/services/" + service_name;
    if (!suffix.empty()) {
        key += "/" + suffix;
    }
    return key;
}

std::string EtcdServiceRegistry::generateHeartbeatKey(const std::string& service_name) {
    return "/services/heartbeat/" + service_name;
}

std::string EtcdServiceRegistry::generateConfigKey(const std::string& service_name, const std::string& config_key) {
    return "/services/config/" + service_name + "/" + config_key;
}