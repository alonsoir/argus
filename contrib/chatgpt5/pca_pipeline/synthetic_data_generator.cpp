// synthetic_data_generator.cpp
// Author: Claude + Alonso
// Created: 09-Enero-2026
// Purpose: Generate synthetic 83-feature events for PCA training pipeline
// Via Appia Quality: documented, error-handled, C++20 compliant

#include <iostream>
#include <vector>
#include <random>
#include <fstream>
#include <string>
#include <stdexcept>

// Number of features
constexpr int NUM_FEATURES = 83;

// Generate a single synthetic feature vector
std::vector<double> generate_feature_vector() {
    std::vector<double> vec(NUM_FEATURES);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<> dist(0.0, 1.0); // standard normal

    for (auto &v : vec) {
        v = dist(gen);
    }
    return vec;
}

// Save synthetic data to CSV (simple format for downstream PCA)
void save_to_csv(const std::vector<std::vector<double>>& data, const std::string& filename) {
    std::ofstream ofs(filename);
    if (!ofs) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    for (const auto& row : data) {
        for (size_t i = 0; i < row.size(); ++i) {
            ofs << row[i];
            if (i != row.size() - 1) ofs << ",";
        }
        ofs << "\n";
    }
    ofs.close();
}

int main() {
    try {
        constexpr size_t NUM_SAMPLES = 20000;
        std::vector<std::vector<double>> dataset;
        dataset.reserve(NUM_SAMPLES);

        for (size_t i = 0; i < NUM_SAMPLES; ++i) {
            dataset.push_back(generate_feature_vector());
        }

        save_to_csv(dataset, "synthetic_features.csv");
        std::cout << "Synthetic dataset generated successfully: synthetic_features.csv\n";
    } catch (const std::exception &e) {
        std::cerr << "[ERROR] " << e.what() << "\n";
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
