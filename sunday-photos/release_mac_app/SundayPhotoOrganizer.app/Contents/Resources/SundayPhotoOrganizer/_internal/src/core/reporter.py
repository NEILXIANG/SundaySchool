"""
Reporting utilities.
"""
import sys
import os
import logging

logger = logging.getLogger(__name__)

class Reporter:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def _hud_rule(self, width: int = 56) -> str:
        # Use unicode if stdout encoding supports it; otherwise fall back.
        enc = (getattr(sys.stdout, "encoding", "") or "").lower()
        if "utf" in enc or sys.platform == "darwin":
            return "━" * width
        return "=" * width

    def _hud_line(self, label: str, text: str) -> str:
        # Fixed width tag for scanability.
        tag = f"[{(label or '').strip().upper():<5}]"
        return f"{tag} {text}"

    def log_step(self, step_info: str) -> None:
        self.logger.info(self._hud_rule())
        self.logger.info(self._hud_line("STEP", step_info))

    def log_info(self, label: str, text: str) -> None:
        self.logger.info(self._hud_line(label, text))

    def log_rule(self) -> None:
        self.logger.info(self._hud_rule())

    def build_run_report(self, stats, organize_stats):
        """创建便于其他模块消费的运行报告快照"""
        pipeline_stats = dict(stats)
        pipeline_stats['students_detected'] = sorted(stats['students_detected'])
        for key in ('start_time', 'end_time'):
            if pipeline_stats[key]:
                pipeline_stats[key] = pipeline_stats[key].isoformat()

        return {
            'organize_stats': organize_stats,
            'pipeline_stats': pipeline_stats
        }

    def print_final_statistics(self, stats, output_dir):
        """打印最终统计信息"""
        self.logger.info(self._hud_rule())
        self.logger.info(self._hud_line("DONE", "处理完成"))
        self.logger.info(self._hud_rule())

        # 计算总耗时
        if stats['start_time'] and stats['end_time']:
            elapsed = stats['end_time'] - stats['start_time']
            minutes, seconds = divmod(elapsed.total_seconds(), 60)
            self.logger.info(self._hud_line("TIME", f"总耗时: {int(minutes)}分{int(seconds)}秒"))

        self.logger.info(self._hud_line("STAT", f"总照片数: {stats['total_photos']}"))
        self.logger.info(self._hud_line("STAT", f"成功识别: {stats['recognized_photos']}"))
        self.logger.info(self._hud_line("STAT", f"unknown_photos: {stats['unknown_photos']}"))
        if 'no_face_photos' in stats:
            self.logger.info(self._hud_line("STAT", f"no_face_photos: {stats.get('no_face_photos', 0)}"))
        if 'error_photos' in stats:
            self.logger.info(self._hud_line("STAT", f"error_photos: {stats.get('error_photos', 0)}"))

        if stats['students_detected']:
            self.logger.info(self._hud_line("STAT", f"识别到的学生: {', '.join(sorted(stats['students_detected']))}"))
        else:
            self.logger.info(self._hud_line("STAT", "识别到的学生: 暂无"))

        self.logger.info(self._hud_line("PATH", f"输出目录: {os.path.abspath(output_dir)}"))
        self.logger.info(self._hud_rule())
