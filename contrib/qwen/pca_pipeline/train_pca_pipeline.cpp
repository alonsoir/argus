// rag/tools/train_pca_pipeline.cpp
/*
 * PCA Training Pipeline for FAISS Dimensionality Reduction
 * Trains faiss::PCAMatrix on synthetic or real embeddings.
 * Validates variance preservation (target ≥96%).
 *
 * Input: embeddings in binary format (float32, row-major)
 * Output: FAISS VectorTransform files (.faiss)
 *
 * Via Appia Quality:
 * - Uses faiss::PCAMatrix (not Eigen) for numerical stability
 * - Validates variance preservation before saving
 * - Clear error handling and logging
 */

#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>
#include <vector>
#include <iostream>
#include <fstream>
#include <cassert>

bool load_embeddings(const std::string& filename, std::vector<float>& embeddings, int& dim) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "❌ Failed to open: " << filename << std::endl;
        return false;
    }

    // Read dimensions
    file.read(reinterpret_cast<char*>(&dim), sizeof(int));
    int n;
    file.read(reinterpret_cast<char*>(&n), sizeof(int));

    embeddings.resize(n * dim);
    file.read(reinterpret_cast<char*>(embeddings.data()), n * dim * sizeof(float));
    file.close();

    std::cout << "✅ Loaded " << n << " embeddings of dimension " << dim << " from " << filename << std::endl;
    return true;
}

void train_and_save_pca(
    const std::vector<float>& embeddings,
    int d_in,
    int d_out,
    const std::string& output_path,
    double min_variance = 0.96
) {
    int n = embeddings.size() / d_in;
    assert(embeddings.size() % d_in == 0);

    std::cout << "Training PCA: " << d_in << " → " << d_out << " (n=" << n << ")" << std::endl;

    // Train FAISS PCA
    auto pca = std::make_unique<faiss::PCAMatrix>(d_in, d_out, 0.0, true);
    pca->train(n, embeddings.data());

    // Validate variance
    double total_var = 0, kept_var = 0;
    for (int i = 0; i < d_in; ++i) total_var += pca->eigenvalues[i];
    for (int i = 0; i < d_out; ++i) kept_var += pca->eigenvalues[i];
    double variance_pct = (kept_var / total_var) * 100;

    std::cout << "Variance preserved: " << variance_pct << "% (target ≥" << (min_variance*100) << "%)" << std::endl;

    if (variance_pct < min_variance * 100) {
        std::cerr << "❌ Variance below threshold! Aborting." << std::endl;
        exit(1);
    }

    // Save
    faiss::write_VectorTransform(pca.get(), output_path.c_str());
    std::cout << "✅ PCA saved to: " << output_path << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc != 5) {
        std::cerr << "Usage: " << argv[0] << " <embeddings.bin> <d_in> <d_out> <output.faiss>\n";
        return 1;
    }

    std::string input_file = argv[1];
    int d_in = std::stoi(argv[2]);
    int d_out = std::stoi(argv[3]);
    std::string output_file = argv[4];

    std::cout << "╔════════════════════════════════════════╗\n";
    std::cout << "║  FAISS PCA Training Pipeline           ║\n";
    std::cout << "╚════════════════════════════════════════╝\n\n";

    std::vector<float> embeddings;
    int dim;
    if (!load_embeddings(input_file, embeddings, dim)) return 1;
    assert(dim == d_in);

    train_and_save_pca(embeddings, d_in, d_out, output_file);

    std::cout << "\n✅ PCA training complete. Ready for ingestion.\n";
    return 0;
}