#!/usr/bin/env python3
"""
ML Defender - PCA Embedder Training
Entrena modelo PCA para reducir 83 features → 64 dimensions
Via Appia Quality - Measured dimensionality reduction
"""

import numpy as np
import argparse
import pickle
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import time

def load_training_data(input_path):
    """Carga datos de entrenamiento desde .npz"""
    print(f"[INFO] Cargando datos desde: {input_path}")

    data = np.load(input_path)
    X = data['data']
    feature_names = data['feature_names']

    print(f"[INFO] ✅ Datos cargados:")
    print(f"       Shape: {X.shape}")
    print(f"       Features: {len(feature_names)}")
    print(f"       Samples: {X.shape[0]:,}")

    return X, feature_names

def train_pca(X, n_components=64, target_variance=0.90):
    """
    Entrena PCA con normalización

    Args:
        X: Training data (n_samples, 83)
        n_components: Target dimensions (default: 64)
        target_variance: Minimum variance to retain (default: 90%)

    Returns:
        scaler, pca, metrics
    """
    print("\n" + "=" * 70)
    print("PHASE 1: Standardization")
    print("=" * 70)

    # Step 1: Standardize features (mean=0, std=1)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"[INFO] ✅ Features standardized:")
    print(f"       Mean: {X_scaled.mean():.6f} (target: 0.0)")
    print(f"       Std:  {X_scaled.std():.6f} (target: 1.0)")

    print("\n" + "=" * 70)
    print(f"PHASE 2: PCA Training (83 → {n_components} dimensions)")
    print("=" * 70)

    # Step 2: Train PCA
    start_time = time.time()
    pca = PCA(n_components=n_components)
    pca.fit(X_scaled)
    training_time = time.time() - start_time

    # Step 3: Calculate metrics
    variance_explained = pca.explained_variance_ratio_.sum()
    cumulative_variance = np.cumsum(pca.explained_variance_ratio_)

    print(f"[INFO] ✅ PCA trained in {training_time:.2f}s")
    print(f"       Components: {n_components}")
    print(f"       Variance explained: {variance_explained*100:.2f}%")
    print(f"       Target variance: {target_variance*100:.2f}%")

    # Per-component variance
    print("\n[INFO] Variance per component (first 10):")
    for i in range(min(10, n_components)):
        print(f"       PC{i+1:2d}: {pca.explained_variance_ratio_[i]*100:5.2f}% "
              f"(cumulative: {cumulative_variance[i]*100:5.2f}%)")

    # Validation
    if variance_explained < target_variance:
        print(f"\n[WARNING] ⚠️  Variance {variance_explained*100:.2f}% < target {target_variance*100:.2f}%")
        print(f"[WARNING] Consider increasing n_components")
    else:
        print(f"\n[INFO] ✅ Target variance achieved!")

    # Metrics
    metrics = {
        'n_components': n_components,
        'variance_explained': variance_explained,
        'cumulative_variance': cumulative_variance.tolist(),
        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
        'training_time_seconds': training_time,
        'n_samples': X.shape[0],
        'n_features_original': X.shape[1]
    }

    return scaler, pca, metrics

def test_transform(scaler, pca, X, n_test=1000):
    """Test PCA transformation"""
    print("\n" + "=" * 70)
    print("PHASE 3: Validation")
    print("=" * 70)

    # Transform sample
    X_test = X[:n_test]

    start_time = time.time()
    X_scaled = scaler.transform(X_test)
    X_transformed = pca.transform(X_scaled)
    transform_time = (time.time() - start_time) / n_test * 1_000_000  # μs per sample

    print(f"[INFO] ✅ Transformation test ({n_test} samples):")
    print(f"       Input shape:  {X_test.shape}")
    print(f"       Output shape: {X_transformed.shape}")
    print(f"       Avg time: {transform_time:.2f} μs per sample")

    # Reconstruction error
    X_reconstructed = pca.inverse_transform(X_transformed)
    reconstruction_error = np.mean((X_scaled - X_reconstructed) ** 2)

    print(f"       Reconstruction MSE: {reconstruction_error:.6f}")

    return transform_time, reconstruction_error

def save_model(scaler, pca, metrics, output_dir):
    """Save trained model and metrics"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save scaler
    scaler_path = output_dir / 'scaler.pkl'
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"\n[INFO] ✅ Scaler saved: {scaler_path}")

    # Save PCA model
    pca_path = output_dir / 'pca_model.pkl'
    with open(pca_path, 'wb') as f:
        pickle.dump(pca, f)
    print(f"[INFO] ✅ PCA model saved: {pca_path}")

    # Save metrics
    metrics_path = output_dir / 'training_metrics.json'
    import json
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[INFO] ✅ Metrics saved: {metrics_path}")

    print(f"\n[INFO] Model files:")
    print(f"       {scaler_path}")
    print(f"       {pca_path}")
    print(f"       {metrics_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Train PCA embedder for ML Defender (83 → 64 dims)"
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='/vagrant/contrib/claude/pca_pipeline/training_data.npz',
        help='Path to training data (.npz)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='/vagrant/contrib/claude/pca_pipeline/models',
        help='Output directory for trained models'
    )
    parser.add_argument(
        '--components', '-c',
        type=int,
        default=64,
        help='Number of PCA components (default: 64)'
    )
    parser.add_argument(
        '--variance', '-v',
        type=float,
        default=0.90,
        help='Target variance to retain (default: 0.90 = 90%%)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("ML Defender - PCA Embedder Training")
    print("=" * 70)
    print(f"Input:      {args.input}")
    print(f"Output:     {args.output}")
    print(f"Components: {args.components}")
    print(f"Target variance: {args.variance*100:.1f}%")
    print("=" * 70)

    # Load data
    X, feature_names = load_training_data(args.input)

    # Train PCA
    scaler, pca, metrics = train_pca(X, args.components, args.variance)

    # Test transformation
    transform_time, reconstruction_error = test_transform(scaler, pca, X)
    metrics['transform_time_us'] = transform_time
    metrics['reconstruction_mse'] = reconstruction_error

    # Save model
    save_model(scaler, pca, metrics, args.output)

    print("\n" + "=" * 70)
    print("✅ PCA EMBEDDER TRAINING COMPLETE")
    print("=" * 70)
    print(f"Variance explained: {metrics['variance_explained']*100:.2f}%")
    print(f"Transform time: {transform_time:.2f} μs/sample")
    print(f"\nNext step: python3 convert_pca_to_onnx.py --input {args.output}")

if __name__ == '__main__':
    main()