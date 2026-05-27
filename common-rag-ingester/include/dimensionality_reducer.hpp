#pragma once

#include <faiss/VectorTransform.h>
#include <memory>
#include <string>
#include <vector>
#include <mutex>

namespace ml_defender {
namespace rag {

/**
 * PCA-based dimensionality reduction using FAISS.
 * Thread-safe for concurrent transform operations.
 *
 * Target: 512 → 128 dimensions with ≥96% variance retention
 */
class DimensionalityReducer {
public:
    /**
     * Create reducer for specific dimensions.
     * @param input_dim Original embedding dimension (default: 384 for all-MiniLM-L6-v2)
     * @param output_dim Reduced dimension (default: 128)
     */
    explicit DimensionalityReducer(int input_dim = 384, int output_dim = 128);

    ~DimensionalityReducer();

    // Non-copyable
    DimensionalityReducer(const DimensionalityReducer&) = delete;
    DimensionalityReducer& operator=(const DimensionalityReducer&) = delete;

    /**
     * Train PCA transformation from training vectors.
     * @param training_data NxD matrix (N samples, D=input_dim)
     * @param n_samples Number of training samples
     * @return Variance ratio retained (0.0-1.0)
     * @throws std::runtime_error if training fails
     */
    float train(const float* training_data, size_t n_samples);

    /**
     * Transform single vector from input_dim → output_dim.
     * Thread-safe after training.
     * @param input Input vector (input_dim)
     * @param output Output vector (output_dim) - caller allocates
     */
    void transform(const float* input, float* output);

    /**
     * Batch transform multiple vectors.
     * More efficient than repeated single transforms.
     * @param input NxD matrix (N vectors, D=input_dim)
     * @param output NxM matrix (N vectors, M=output_dim) - caller allocates
     * @param n_vectors Number of vectors
     */
    void transform_batch(const float* input, float* output, size_t n_vectors);

    /**
     * Save trained PCA model to disk.
     * @param filepath Path to save (e.g., /shared/models/pca/reducer_384_128.faiss)
     */
    void save(const std::string& filepath);

    /**
     * Load trained PCA model from disk.
     * @param filepath Path to load
     * @throws std::runtime_error if file doesn't exist or is corrupted
     */
    void load(const std::string& filepath);

    /**
     * Check if model is trained and ready.
     */
    bool is_trained() const { return trained_; }

    /**
     * Get input dimension.
     */
    int input_dim() const { return input_dim_; }

    /**
     * Get output dimension.
     */
    int output_dim() const { return output_dim_; }

    /**
     * Get variance ratio from last training (0.0 if not trained).
     */
    float variance_ratio() const { return variance_ratio_; }

private:
    int input_dim_;
    int output_dim_;
    float variance_ratio_;
    bool trained_;

    std::unique_ptr<faiss::PCAMatrix> pca_;
    mutable std::mutex transform_mutex_;  // Protect concurrent transforms
};

} // namespace rag
} // namespace ml_defender