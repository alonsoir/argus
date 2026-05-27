/**
* @file synthetic_data_generator.cpp
 * @brief Generates high-dimensional synthetic data for PCA architecture validation.
 * @author Gemini 3.5 Flash (Collaboration with Alonso)
 * @quality Via Appia - C++20 Standard
 */

#include <iostream>
#include <vector>
#include <random>
#include <fstream>
#include <filesystem>

namespace fs = std::filesystem;

int main(int argc, char* argv[]) {
    const size_t num_samples = 20000;
    const size_t num_features = 83;
    const std::string output_path = "synthetic_features.bin";

    std::cout << "🚀 Generating " << num_samples << " synthetic samples with "
              << num_features << " features..." << std::endl;

    std::vector<float> data(num_samples * num_features);

    // Usamos una distribución normal para simular varianza real
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<float> d(0.0f, 1.0f);

    for (size_t i = 0; i < data.size(); ++i) {
        data[i] = d(gen);
    }

    std::ofstream out(output_path, std::ios::binary);
    if (!out) {
        std::cerr << "❌ Error: Could not create output file." << std::endl;
        return 1;
    }

    out.write(reinterpret_cast<const char*>(data.data()), data.size() * sizeof(float));
    std::cout << "✅ Synthetic data saved to: " << output_path << " ("
              << fs::file_size(output_path) / 1024 << " KB)" << std::endl;

    return 0;
}