#include "dimensionality_reducer.hpp"
#include <faiss/index_io.h>
#include <stdexcept>
#include <cstring>
#include <iostream>

namespace ml_defender {
namespace rag {

DimensionalityReducer::DimensionalityReducer(int input_dim, int output_dim)
    : input_dim_(input_dim)
    , output_dim_(output_dim)
    , variance_ratio_(0.0f)
    , trained_(false)
    , pca_(nullptr)
{
    if (input_dim <= 0 || output_dim <= 0) {
        throw std::invalid_argument("Dimensions must be positive");
    }
    if (output_dim > input_dim) {
        throw std::invalid_argument("Output dimension cannot exceed input dimension");
    }

    // Create PCA matrix (not trained yet)
    pca_ = std::make_unique<faiss::PCAMatrix>(input_dim, output_dim, 0.0f, false);
}

DimensionalityReducer::~DimensionalityReducer() = default;

float DimensionalityReducer::train(const float* training_data, size_t n_samples) {
    if (!training_data) {
        throw std::invalid_argument("Training data cannot be null");
    }
    if (n_samples < static_cast<size_t>(output_dim_)) {
        throw std::invalid_argument("Need at least output_dim samples for PCA");
    }

    try {
        // Train PCA matrix
        pca_->train(n_samples, training_data);

        // Calculate variance ratio from eigenvalues
        float total_variance = 0.0f;
        float retained_variance = 0.0f;

        // FAISS stores eigenvalues in pca_->eigenvalues
        // They're sorted in descending order
        for (int i = 0; i < input_dim_; ++i) {
            total_variance += pca_->eigenvalues[i];
            if (i < output_dim_) {
                retained_variance += pca_->eigenvalues[i];
            }
        }

        variance_ratio_ = (total_variance > 0.0f) ? (retained_variance / total_variance) : 0.0f;
        trained_ = true;

        std::cout << "[DimensionalityReducer] Training complete:\n"
                  << "  Input dim: " << input_dim_ << "\n"
                  << "  Output dim: " << output_dim_ << "\n"
                  << "  Samples: " << n_samples << "\n"
                  << "  Variance retained: " << (variance_ratio_ * 100.0f) << "%\n";

        if (variance_ratio_ < 0.96f) {
            std::cerr << "[WARNING] Variance ratio " << (variance_ratio_ * 100.0f)
                      << "% below 96% target. Consider increasing output_dim.\n";
        }

        return variance_ratio_;

    } catch (const std::exception& e) {
        trained_ = false;
        throw std::runtime_error(std::string("PCA training failed: ") + e.what());
    }
}

void DimensionalityReducer::transform(const float* input, float* output) {
    if (!trained_) {
        throw std::runtime_error("Cannot transform: model not trained");
    }
    if (!input || !output) {
        throw std::invalid_argument("Input/output pointers cannot be null");
    }

    std::lock_guard<std::mutex> lock(transform_mutex_);
    pca_->apply_noalloc(1, input, output);
}

void DimensionalityReducer::transform_batch(const float* input, float* output, size_t n_vectors) {
    if (!trained_) {
        throw std::runtime_error("Cannot transform: model not trained");
    }
    if (!input || !output) {
        throw std::invalid_argument("Input/output pointers cannot be null");
    }
    if (n_vectors == 0) {
        return;
    }

    std::lock_guard<std::mutex> lock(transform_mutex_);
    pca_->apply_noalloc(n_vectors, input, output);
}

void DimensionalityReducer::save(const std::string& filepath) {
    if (!trained_) {
        throw std::runtime_error("Cannot save: model not trained");
    }

    try {
        faiss::write_VectorTransform(pca_.get(), filepath.c_str());
        std::cout << "[DimensionalityReducer] Model saved: " << filepath << "\n";
    } catch (const std::exception& e) {
        throw std::runtime_error(std::string("Failed to save model: ") + e.what());
    }
}

void DimensionalityReducer::load(const std::string& filepath) {
    try {
        // Load PCA matrix from file
        auto loaded = faiss::read_VectorTransform(filepath.c_str());

        // Verify it's actually a PCAMatrix
        auto loaded_pca = dynamic_cast<faiss::PCAMatrix*>(loaded);
        if (!loaded_pca) {
            delete loaded;
            throw std::runtime_error("File does not contain a PCAMatrix");
        }

        // Verify dimensions match
        if (loaded_pca->d_in != input_dim_ || loaded_pca->d_out != output_dim_) {
            delete loaded;
            throw std::runtime_error("Dimension mismatch: expected " +
                                   std::to_string(input_dim_) + "→" + std::to_string(output_dim_) +
                                   ", got " + std::to_string(loaded_pca->d_in) + "→" +
                                   std::to_string(loaded_pca->d_out));
        }

        pca_.reset(loaded_pca);
        trained_ = true;

        // Recalculate variance ratio
        float total_variance = 0.0f;
        float retained_variance = 0.0f;
        for (int i = 0; i < input_dim_; ++i) {
            total_variance += pca_->eigenvalues[i];
            if (i < output_dim_) {
                retained_variance += pca_->eigenvalues[i];
            }
        }
        variance_ratio_ = (total_variance > 0.0f) ? (retained_variance / total_variance) : 0.0f;

        std::cout << "[DimensionalityReducer] Model loaded: " << filepath << "\n"
                  << "  Variance retained: " << (variance_ratio_ * 100.0f) << "%\n";

    } catch (const std::exception& e) {
        trained_ = false;
        throw std::runtime_error(std::string("Failed to load model: ") + e.what());
    }
}

} // namespace rag
} // namespace ml_defender