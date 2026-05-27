#ifndef LLAMA_INTEGRATION_HPP
#define LLAMA_INTEGRATION_HPP

#include <string>
#include <memory>

class LlamaIntegration {
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;

public:
    LlamaIntegration();
    ~LlamaIntegration();
    
    // Eliminar copia
    LlamaIntegration(const LlamaIntegration&) = delete;
    LlamaIntegration& operator=(const LlamaIntegration&) = delete;
    
    bool loadModel(const std::string& model_path);
    std::string generateResponse(const std::string& prompt);
};

#endif // LLAMA_INTEGRATION_HPP