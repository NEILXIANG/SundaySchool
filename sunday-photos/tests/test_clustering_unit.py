import numpy as np
import pytest
from src.core.clustering import UnknownClustering

class TestUnknownClustering:
    def test_initialization(self):
        clusterer = UnknownClustering(tolerance=0.4, min_cluster_size=2)
        assert clusterer.tolerance == 0.4
        assert clusterer.min_cluster_size == 2
        assert clusterer.clusters == {}

    def test_add_single_face(self):
        clusterer = UnknownClustering()
        encoding = np.array([0.1, 0.2, 0.3])
        clusterer.add_faces("path/to/img1.jpg", [encoding])
        assert len(clusterer.clusters) == 1
        assert len(clusterer.clusters[1]) == 1
        assert clusterer.clusters[1][0][0] == "path/to/img1.jpg"

    def test_clustering_logic(self):
        clusterer = UnknownClustering(tolerance=0.1, min_cluster_size=2)
        
        # Face A
        enc_a = np.array([1.0, 0.0, 0.0])
        # Face A' (very close to A)
        enc_a_prime = np.array([0.99, 0.01, 0.0])
        # Face B (far from A)
        enc_b = np.array([0.0, 1.0, 0.0])

        clusterer.add_faces("img_a.jpg", [enc_a])
        clusterer.add_faces("img_a_prime.jpg", [enc_a_prime])
        clusterer.add_faces("img_b.jpg", [enc_b])

        # Should have 2 clusters
        # Cluster 1: A and A'
        # Cluster 2: B
        assert len(clusterer.clusters) == 2
        
        # Check results
        results = clusterer.get_results()
        # Only clusters with size >= 2 should be returned
        assert len(results) == 1
        assert "Unknown_Person_1" in results
        assert len(results["Unknown_Person_1"]) == 2
        assert "img_a.jpg" in results["Unknown_Person_1"]
        assert "img_a_prime.jpg" in results["Unknown_Person_1"]

    def test_min_cluster_size(self):
        clusterer = UnknownClustering(min_cluster_size=3)
        enc = np.array([1.0, 0.0])
        clusterer.add_faces("1.jpg", [enc])
        clusterer.add_faces("2.jpg", [enc])
        
        # Size is 2, min is 3 -> should return empty
        assert len(clusterer.get_results()) == 0
        
        clusterer.add_faces("3.jpg", [enc])
        # Size is 3 -> should return
        assert len(clusterer.get_results()) == 1

    def test_invalid_encoding_handling(self):
        clusterer = UnknownClustering()
        # Should not crash
        clusterer.add_faces("bad.jpg", ["not-an-array"])
        assert len(clusterer.clusters) == 0

    def test_cosine_distance(self):
        a = np.array([1, 0])
        b = np.array([0, 1])
        dist = UnknownClustering._cosine_distance(a, b)
        assert abs(dist - 1.0) < 1e-6 # Orthogonal -> dist 1

        c = np.array([1, 0])
        dist_same = UnknownClustering._cosine_distance(a, c)
        assert abs(dist_same - 0.0) < 1e-6 # Same -> dist 0
