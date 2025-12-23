"""
教师辅助模块
为没有计算机基础的教师提供友好的错误提示和操作指导
"""

import os
import sys
import traceback
from pathlib import Path

class TeacherHelper:
    """教师辅助类"""
    
    def __init__(self):
        self.setup_chinese_messages()
    
    def setup_chinese_messages(self):
        """设置中文友好消息"""
        self.messages = {
            # 文件相关错误
            'file_not_found': {
                'title': '📁 找不到文件或文件夹',
                'explanation': '程序需要访问某个文件或文件夹，但是没有找到它。',
                'solutions': [
                    '检查您是否在正确的文件夹中运行程序',
                    '确保文件夹名拼写正确（注意大小写）',
                    '确认文件确实存在于指定的位置',
                    '检查文件夹是否被移动或删除'
                ]
            },
            
            # 权限相关错误
            'permission_denied': {
                'title': '🔒 没有权限访问文件',
                'explanation': '程序试图访问文件，但系统拒绝了权限。',
                'solutions': [
                    '关闭可能正在使用这些文件的其他程序',
                    '尝试以管理员身份运行程序',
                    '检查文件夹是否被设置为只读',
                    '将程序和数据放在您有权限的文件夹中'
                ]
            },
            
            # 内存相关错误
            'memory_error': {
                'title': '🧠 电脑内存不足',
                'explanation': '程序运行需要更多内存，但当前电脑内存不够。',
                'solutions': [
                    '关闭其他不需要的程序释放内存',
                    '减少一次处理的照片数量',
                    '重启电脑清理内存',
                    '考虑在内存更大的电脑上运行'
                ]
            },
            
            # 人脸识别相关错误
            'face_recognition_error': {
                'title': '👤 人脸识别遇到问题',
                'explanation': '程序无法正确识别照片中的人脸。',
                'solutions': [
                    '确保照片中包含清晰、完整的人脸',
                    '照片不要过暗或过亮',
                    '避免照片中人脸太小或模糊',
                    '使用高质量的照片文件',
                    '检查照片格式是否支持（推荐.jpg格式）'
                ]
            },
            
            # 依赖包相关错误
            'import_error': {
                'title': '📦 缺少程序组件',
                'explanation': '程序运行需要一些额外的组件，但系统中没有安装。',
                'solutions': [
                    '运行命令：pip install -r requirements.txt',
                    '确保网络连接正常',
                    '如果安装失败，尝试使用管理员权限',
                    '联系技术人员协助安装'
                ]
            },
            
            # 网络相关错误
            'network_error': {
                'title': '🌐 网络连接问题',
                'explanation': '程序需要访问网络但无法建立连接。',
                'solutions': [
                    '检查网络连接是否正常',
                    '尝试打开网页确认网络可用',
                    '检查防火墙设置',
                    '联系网络管理员'
                ]
            },
            
            # 配置文件错误
            'config_error': {
                'title': '⚙️ 配置文件问题',
                'explanation': '程序的配置文件有错误或格式不正确。',
                'solutions': [
                    '检查配置文件是否存在',
                    '确保JSON格式正确（括号、引号等）',
                    '可以删除配置文件让程序使用默认设置',
                    '参考示例配置文件重新创建'
                ]
            },
            
            # 照片格式错误
            'photo_format_error': {
                'title': '🖼️ 照片格式不支持',
                'explanation': '照片文件格式不受程序支持。',
                'solutions': [
                    '使用常见的照片格式：.jpg .jpeg .png',
                    '将其他格式转换为支持的格式',
                    '使用图片转换工具或在线转换',
                    '避免使用损坏的照片文件'
                ]
            },

            # Windows 常见：路径过长
            'path_too_long': {
                'title': '📏 文件路径太长（Windows 常见）',
                'explanation': 'Windows 在某些情况下对文件路径长度有限制，路径太深时会导致复制/写入失败。',
                'solutions': [
                    '把工作目录放得更“浅”：例如把桌面文件夹改放到 C:/SundaySchoolPhotoOrganizer/（或把工程目录移到更短路径）',
                    '缩短学生文件夹名/照片文件名（避免超长名字）',
                    '避免过深的日期/多层子目录',
                    '如有条件：在 Windows 系统设置中启用“长路径支持”（需要管理员权限）'
                ]
            },

            # 控制台编码问题
            'console_encoding': {
                'title': '🔤 控制台文字显示异常（可能是编码问题）',
                'explanation': '在 Windows 的某些终端/字体设置下，中文/特殊符号可能显示为乱码，但不一定影响实际整理结果。',
                'solutions': [
                    '优先使用 Windows Terminal 或 PowerShell 打开并运行',
                    '双击运行时请尽量使用提供的 .bat 启动脚本（会尝试切换到 UTF-8）',
                    '如果仍乱码：在终端里执行 chcp 65001 后再运行',
                    '如需要求助：请优先发送 logs/ 里的最新日志（日志是 UTF-8）'
                ]
            }
        }
    
    def get_friendly_error(self, error, context=""):
        """获取友好的错误信息"""
        error_str = str(error)
        error_type = type(error).__name__

        # Windows path-too-long: WinError 206 / ENAMETOOLONG
        try:
            winerror = getattr(error, 'winerror', None)
        except Exception:
            winerror = None
        
        # 根据错误类型返回相应的友好消息
        if error_type == "FileNotFoundError" or "找不到文件" in error_str:
            return self.format_message('file_not_found', context)
        elif error_type == "PermissionError" or "Permission denied" in error_str or "权限" in error_str:
            return self.format_message('permission_denied', context)
        elif winerror == 206 or "WinError 206" in error_str or "File name too long" in error_str or "ENAMETOOLONG" in error_str:
            return self.format_message('path_too_long', context)
        elif error_type == "UnicodeEncodeError" or "UnicodeEncodeError" in error_str:
            return self.format_message('console_encoding', context)
        elif error_type == "MemoryError" or "内存" in error_str:
            return self.format_message('memory_error', context)
        elif "face_recognition" in error_str.lower():
            return self.format_message('face_recognition_error', context)
        elif error_type in ["ImportError", "ModuleNotFoundError"] or "ImportError" in error_str or "ModuleNotFoundError" in error_str:
            return self.format_message('import_error', context)
        elif "network" in error_str.lower() or "connection" in error_str.lower():
            return self.format_message('network_error', context)
        elif "config" in error_str.lower() or "JSON" in error_str:
            return self.format_message('config_error', context)
        elif "format" in error_str.lower() and "photo" in error_str.lower():
            return self.format_message('photo_format_error', context)
        else:
            return self.get_general_error(error, context)
    
    def format_message(self, message_key, context=""):
        """格式化消息"""
        if message_key not in self.messages:
            return self.get_general_error("未知错误", context)
        
        msg = self.messages[message_key]
        
        formatted = f"""
{msg['title']}

📖 问题说明：
{msg['explanation']}

💡 解决办法：
"""
        
        for i, solution in enumerate(msg['solutions'], 1):
            formatted += f"   {i}. {solution}\n"
        
        if context:
            formatted += f"\n📍 相关信息：{context}\n"
        
        formatted += "\n💬 如果问题仍然存在，请联系技术支持。"
        
        return formatted
    
    def get_general_error(self, error, context=""):
        """获取通用错误消息"""
        return f"""
⚠️ 程序遇到了意外问题

📖 问题说明：
{str(error)}

💡 一般解决方法：
   1. 重新启动程序
   2. 检查输入数据是否正确
   3. 确保程序在正确的文件夹中运行
   4. 检查是否有其他程序冲突

📍 相关信息：{context}

💬 如果问题持续出现，请记录错误信息并联系技术支持。
"""
    
    def show_operation_guide(self, operation):
        """显示操作指南"""
        guides = {
            'setup': """
🚀 程序设置指南

📋 准备工作：
    1. 确保已安装 Python 3.10+（本仓库以 Python 3.14 环境测试）
   2. 安装所需的程序包：pip install -r requirements.txt
   3. 确保在正确的项目文件夹中运行程序

📁 文件夹设置：
    • input/ - 输入数据
      └── student_photos/ - 学生参考照片
      └── class_photos/ - 待整理的课堂照片
   • output/ - 整理后的照片输出
   • logs/ - 程序运行日志

📸 照片要求：
    • 学生参考照（唯一方式）：student_photos/学生名/ 里放照片（文件名随意）
   • 照片清晰度：确保人脸清晰可见
    • 照片格式：推荐使用 .jpg/.png

🎯 运行程序：
   • 简单模式：python run.py
   • 高级模式：python src/main.py [参数]
""",
            
                'photo_naming': """
📸 学生参考照放置指南（唯一方式）

✅ 正确放法：
    • 在 input/student_photos 里为每个学生创建一个文件夹：
        input/student_photos/Alice(Senior)/
        input/student_photos/Bob(Junior)/
    • 把该学生的参考照片放进对应文件夹
    • 文件名随意（不用改名），只要不重名即可

❌ 常见错误：
    • 把照片直接放在 input/student_photos 根目录
    • 在学生文件夹里再建更深一层子文件夹
    • 学生文件夹为空

💡 最佳实践：
    • 每个学生准备 2-5 张不同角度的清晰正脸照
    • 参考照尽量只拍该学生本人（避免多人合照）
    • 遮挡少、光线好、人脸不要太小
""",
            
            'troubleshooting': """
🔧 问题解决指南

🚨 常见问题：

❓ 程序提示"找不到文件"
   ✅ 检查是否在正确文件夹运行
   ✅ 确认文件夹名称拼写正确

❓ 照片无法识别人脸
   ✅ 确保照片清晰、人脸完整
    ✅ 给该学生补 2-3 张清晰正脸参考照
    ✅ 参考照避免多人合照
   ✅ 使用质量更好的照片

❓ 程序运行很慢
   ✅ 关闭其他程序释放内存
   ✅ 减少一次处理的照片数量
   ✅ 确保电脑性能足够

❓ 出现错误提示
   ✅ 仔细阅读错误信息
   ✅ 按照提示进行修复
   ✅ 无法解决时联系技术支持

📞 技术支持：
   • 保存错误截图
   • 记录操作步骤
   • 提供详细问题描述
"""
        }
        
        return guides.get(operation, "没有找到相关的操作指南。")

def create_friendly_exception_handler():
    """创建友好的异常处理器"""
    helper = TeacherHelper()
    
    def friendly_exception_handler(exc_type, exc_value, exc_traceback):
        """友好的异常处理函数"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 用户中断
            print("\n\n⏹️ 程序已被用户停止")
            return
        
        print("\n" + "="*60)
        print("😕 程序遇到了问题")
        print("="*60)
        
        # 获取上下文信息
        tb = traceback.extract_tb(exc_traceback)
        if tb:
            last_frame = tb[-1]
            context = f"文件：{last_frame.filename}，行号：{last_frame.lineno}，函数：{last_frame.name}"
        else:
            context = "未知位置"
        
        # 显示友好错误信息
        friendly_msg = helper.get_friendly_error(exc_value, context)
        print(friendly_msg)
        
        # 询问是否显示详细错误
        try:
            show_details = input("\n🔍 是否显示技术详细信息？(y/n): ").lower().strip()
            if show_details in ['y', 'yes', '是']:
                print("\n" + "-"*40)
                print("📋 技术详细信息：")
                print("-"*40)
                traceback.print_exception(exc_type, exc_value, exc_traceback)
        except:
            pass
        
        print("="*60)
    
    return friendly_exception_handler

# 全局设置友好的异常处理器
if __name__ != "__main__":
    sys.excepthook = create_friendly_exception_handler()