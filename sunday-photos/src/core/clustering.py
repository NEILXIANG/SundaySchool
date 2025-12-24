"""
未知人脸聚类模块

功能：
- 接收所有未识别的人脸编码
- 使用贪婪策略进行聚类
- 生成 "Unknown_Person_X" 的分组建议
"""

import numpy as np
import logging
from typing import List, Dict, Tuple

# 尝试导入 face_recognition，如果失败则不启用聚类（虽然理论上已安装）
try:
    import face_recognition
except ImportError:
    face_recognition = None

logger = logging.getLogger(__name__)

class UnknownClustering:
    def __init__(self, tolerance: float = 0.45, min_cluster_size: int = 2):
        """
        初始化聚类器
        :param tolerance: 聚类判定阈值。建议比识别阈值(0.6)更严格，以减少误聚类。
        :param min_cluster_size: 最小聚类大小。只有当组内照片数 >= 该值时才会输出 Unknown_Person_X。
        """
        self.tolerance = tolerance
        self.min_cluster_size = max(1, int(min_cluster_size))
        # clusters: cluster_id -> list of (file_path, encoding)
        self.clusters: Dict[int, List[Tuple[str, np.ndarray]]] = {}
        self.next_cluster_id = 1

    def add_faces(self, path: str, encodings: List[np.ndarray]):
        """
        添加一张照片中的未知人脸编码
        :param path: 照片路径
        :param encodings: 该照片中检测到的未知人脸编码列表
        """
        if face_recognition is None:
            return

        for encoding in encodings:
            try:
                if not isinstance(encoding, np.ndarray):
                    encoding = np.asarray(encoding, dtype=float)
            except Exception:
                continue
            self._add_one(path, encoding)

    def _add_one(self, path: str, encoding: np.ndarray):
        best_cluster_id = -1
        min_dist = 1.0

        # 简单的贪婪聚类：与现有簇的中心（或所有点）比较
        # 这里采用与簇内所有点的平均距离作为判定标准
        for cluster_id, items in self.clusters.items():
            cluster_encodings = [item[1] for item in items]
            
            # 计算与簇内所有点的距离
            distances = face_recognition.face_distance(cluster_encodings, encoding)
            avg_dist = np.mean(distances)
            
            if avg_dist < min_dist:
                min_dist = avg_dist
                best_cluster_id = cluster_id

        # 如果找到了足够近的簇，加入该簇
        if best_cluster_id != -1 and min_dist < self.tolerance:
            self.clusters[best_cluster_id].append((path, encoding))
        else:
            # 否则创建新簇
            self.clusters[self.next_cluster_id] = [(path, encoding)]
            self.next_cluster_id += 1

    def get_results(self) -> Dict[str, List[str]]:
        """
        获取聚类结果
        :return: {"Unknown_Person_1": [path1, path2], ...}
        """
        results = {}
        # 按簇大小排序，大的在前
        sorted_clusters = sorted(self.clusters.items(), key=lambda x: len(x[1]), reverse=True)
        
        # 重新编号，确保 Unknown_Person_1 是照片最多的
        for new_id, (old_id, items) in enumerate(sorted_clusters, 1):
            # 只有当簇内照片数量 >= 2 时才认为是有效聚类？
            # 或者全部输出？为了方便老师筛选，全部输出比较好，或者只输出 >= 2 的。
            # 考虑到 "Unknown" 文件夹可能很乱，如果只有 1 张，其实没必要建文件夹。
            # 但为了完整性，还是全部输出，或者加个参数控制。
            # 这里策略：如果只有1张，归类为 "Unknown_Singles" 或者直接不归类（保持在根目录）？
            # 现在的需求是 "Unknown_Person_X"，通常暗示有多张。
            # 让我们只返回 >= 2 张的聚类，剩下的归为 "Others" 或不返回（由调用者处理剩余的）。
            
            if len(items) < self.min_cluster_size:
                continue
                
            name = f"Unknown_Person_{new_id}"
            paths = [item[0] for item in items]
            results[name] = paths
            
        return results
