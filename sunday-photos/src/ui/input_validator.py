"""
输入验证模块
为教师提供友好的输入验证和指导
"""

import os
import re
from pathlib import Path

class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        self.setup_validation_rules()
        self.setup_error_messages()
    
    def setup_validation_rules(self):
        """设置验证规则"""
        self.photo_name_pattern = re.compile(
            r'^(?P<name>[A-Za-z0-9\u4e00-\u9fa5]+)(?:_(?P<seq>[1-9]\d*))?\.(jpg|jpeg|png)$',
            re.IGNORECASE
        )
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    
    def setup_error_messages(self):
        """设置错误消息"""
        self.error_messages = {
            'photo_name': {
                'title': '📸 学生照片文件名格式不正确',
                'correct_format': '正确格式：姓名[可选_序号].扩展名',
                'examples': ['Alice.jpg', 'Bob_2.png', '张三.jpg', '李四_1.jpg'],
                'common_mistakes': [
                    '使用特殊符号：Alice!.jpg',
                    '序号格式错误：张三_01.jpg',
                    '扩展名错误：张三_1.txt'
                ]
            }
        }
    
    def validate_photo_name(self, filename):
        """验证照片文件名"""
        is_valid = bool(self.photo_name_pattern.match(filename))
        
        if not is_valid:
            return {
                'valid': False,
                'message': self.get_photo_name_error_message(filename)
            }
        
        return {
            'valid': True,
            'name': self.extract_student_name(filename),
            'sequence': self.extract_sequence_number(filename)
        }
    
    def extract_student_name(self, filename):
        """提取学生姓名"""
        match = self.photo_name_pattern.match(filename)
        if match:
            return match.group('name')
        return None
    
    def extract_sequence_number(self, filename):
        """提取序号"""
        match = self.photo_name_pattern.match(filename)
        if match:
            seq = match.group('seq')
            if seq is not None:
                return int(seq)
        return None
    
    def get_photo_name_error_message(self, filename):
        """获取照片文件名错误消息"""
        msg = self.error_messages['photo_name']
        
        error_msg = f"""
{msg['title']}

📁 错误文件：{filename}

✅ 正确格式：{msg['correct_format']}

📝 示例：
"""
        for example in msg['examples']:
            error_msg += f"   • {example}\n"
        
        error_msg += "\n❌ 常见错误：\n"
        for mistake in msg['common_mistakes']:
            error_msg += f"   • {mistake}\n"
        
        error_msg += """
💡 修复建议：
    1. 使用真实姓名（中文或英文）
    2. 如需多张参考照，可添加序号：姓名_序号
    3. 序号从1开始，不要用01、02这样的格式
    4. 使用照片文件的扩展名(.jpg或.png)
"""
        
        return error_msg
    
    def validate_directory_exists(self, dir_path, dir_name="文件夹"):
        """验证目录是否存在"""
        if not os.path.exists(dir_path):
            return {
                'valid': False,
                'message': f"""
📁 找不到{dir_name}

❌ 路径不存在：{dir_path}

💡 解决办法：
   1. 确认文件夹路径拼写正确
   2. 检查是否需要创建该文件夹
   3. 确保在正确的项目目录中运行程序

📂 如果需要创建文件夹：
   • Windows：在文件资源管理器中右键 → 新建文件夹
   • Mac：在Finder中右键 → 新建文件夹
   • 或使用命令：mkdir 文件夹名
"""
            }
        
        if not os.path.isdir(dir_path):
            return {
                'valid': False,
                'message': f"""
📁 {dir_name}不是文件夹

❌ 路径存在但不是文件夹：{dir_path}

💡 解决办法：
   1. 检查路径是否指向文件而不是文件夹
   2. 删除同名文件后创建文件夹
   3. 使用不同的文件夹名称
"""
            }
        
        return {'valid': True}
    
    def validate_photo_file(self, file_path):
        """验证照片文件"""
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'message': f"""
📸 找不到照片文件

❌ 文件不存在：{file_path}

💡 解决办法：
   1. 检查文件路径是否正确
   2. 确认文件名拼写正确
   3. 确保文件没有被移动或删除
"""
            }
        
        # 检查文件扩展名
        ext = Path(file_path).suffix.lower()
        if ext not in self.supported_extensions:
            return {
                'valid': False,
                'message': f"""
🖼️ 照片格式不支持

❌ 不支持的格式：{ext}
✅ 支持的格式：{', '.join(self.supported_extensions)}

💡 解决办法：
   1. 将照片转换为支持的格式
   2. 使用图片编辑软件另存为.jpg或.png格式
   3. 确保文件扩展名正确
"""
            }
        
        # 检查文件大小（避免空文件）
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {
                'valid': False,
                'message': f"""
📸 照片文件为空

❌ 文件大小：0字节
📁 文件路径：{file_path}

💡 解决办法：
   1. 文件可能损坏，请重新保存或获取原始文件
   2. 检查文件是否完整上传
   3. 尝试用图片查看器打开确认文件正常
"""
            }
        
        return {'valid': True}
    
    def validate_student_photos_directory(self, dir_path):
        """验证学生照片目录"""
        dir_result = self.validate_directory_exists(dir_path, "学生照片文件夹")
        if not dir_result['valid']:
            return dir_result
        
        # 检查目录中是否有照片
        photo_files = []
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            if os.path.isfile(file_path):
                ext = Path(file).suffix.lower()
                if ext in self.supported_extensions:
                    photo_files.append(file)
        
        if not photo_files:
            return {
                'valid': False,
                'message': f"""
📁 学生照片文件夹为空

📂 文件夹路径：{dir_path}

💡 解决办法：
   1. 将学生照片文件放入此文件夹
   2. 确保照片文件格式正确(.jpg, .png等)
   3. 检查是否放错了文件夹

📸 照片要求：
    • 文件名格式：姓名[可选_序号].jpg（如：Alice.jpg 或 张三_1.jpg）
    • 照片清晰，包含完整人脸
    • 每个学生至少1-2张照片
"""
            }
        
        # 检查文件名格式
        invalid_files = []
        valid_files = []
        
        for photo_file in photo_files:
            validation = self.validate_photo_name(photo_file)
            if validation['valid']:
                valid_files.append(photo_file)
            else:
                invalid_files.append(photo_file)
        
        if invalid_files:
            return {
                'valid': False,
                'message': f"""
📁 部分学生照片文件名不正确

📂 文件夹路径：{dir_path}

✅ 正确命名的文件：{len(valid_files)}个
❌ 错误命名的文件：{len(invalid_files)}个

错误的文件名：
"""
                + '\n'.join([f"   • {file}" for file in invalid_files[:5]])
                + (f"\n   ... 还有{len(invalid_files)-5}个文件" if len(invalid_files) > 5 else "")
                + self.get_photo_name_error_message("示例文件名")
            }
        
        return {
            'valid': True,
            'photo_count': len(valid_files),
            'message': f"✅ 找到{len(valid_files)}张格式正确的学生照片"
        }
    
    def validate_tolerance_parameter(self, tolerance_str):
        """验证识别阈值参数"""
        try:
            tolerance = float(tolerance_str)
        except ValueError:
            return {
                'valid': False,
                'message': f"""
🎛️ 识别阈值格式错误

❌ 输入值：{tolerance_str}
✅ 正确格式：0到1之间的小数

💡 参考值：
   • 0.4 - 比较严格，要求高质量照片
   • 0.6 - 标准设置，适合大多数情况
   • 0.8 - 比较宽松，可能误识别

💡 使用方法：
   • 命令行：--tolerance 0.6
   • 或者直接使用默认值
"""
            }
        
        if not 0 <= tolerance <= 1:
            return {
                'valid': False,
                'message': f"""
🎛️ 识别阈值超出范围

❌ 输入值：{tolerance}
✅ 正确范围：0到1之间

💡 建议值：
   • 0.4 - 严格模式（高质量照片）
   • 0.6 - 标准模式（推荐）
   • 0.8 - 宽松模式（质量较低照片）

🔄 请重新设置参数
"""
            }
        
        return {
            'valid': True,
            'tolerance': tolerance,
            'message': f"✅ 识别阈值设置正确：{tolerance}"
        }

def show_operation_guide(guide_type):
    """显示操作指南"""
    guides = {
        'photo_preparation': """
📸 学生照片准备指南

🎯 目标：准备高质量的学生参考照片

📋 照片要求：
    • 格式：优先使用.jpg，也可以.png
    • 大小：不做限制，超大图片可能占用较多内存（资源不足时程序会提示）
   • 清晰度：人脸清晰，细节可见
   • 光线：光线充足，避免过暗或过曝
   • 背景：简洁背景，避免杂乱

📝 命名规范：
   • 格式：姓名_序号.扩展名
   • 示例：张三_1.jpg, 李四_1.jpg
   • 要求：使用中文名字，序号从1开始

🚫 避免问题：
   • 避免多人合照
   • 避免侧脸或背影
   • 避免表情夸张
   • 避免遮挡（口罩、帽子等）

💡 最佳实践：
   • 每个学生准备2-3张不同角度的照片
   • 照片包含正面和侧面
   • 确保表情自然
""",
        
          'file_organization': """
📁 文件夹组织指南

🏗️ 项目结构：
sunday-photos/
├── input/                  # 输入数据主文件夹
│   ├── student_photos/     # 学生参考照片（姓名或姓名_序号）
│   └── class_photos/       # 课堂合照（按日期子目录，如 2025-12-08/）
├── output/                 # 整理后的输出（按学生/日期归档）
├── src/                    # 程序源码
├── logs/                   # 运行日志
├── config.json             # 配置文件
└── run.py                  # 启动程序

📂 具体操作：
    1️⃣ 创建 input 文件夹（如果不存在）
    2️⃣ 在 input 中创建 student_photos 文件夹
    3️⃣ 将学生照片放入 student_photos（如 Alice.jpg 或 张三_1.jpg）
    4️⃣ 在 input 中创建 class_photos/日期 子文件夹（如 2025-12-08）
    5️⃣ 将课堂合照放入对应日期的子文件夹

💡 注意事项：
    • 文件夹名称必须准确
    • 日期目录推荐使用 YYYY-MM-DD 命名
    • 确保照片在正确位置
""",
        
        'troubleshooting': """
🔧 问题解决指南

❓ 常见问题及解决方法：

🔍 问题：程序提示"找不到文件"
✅ 解决：
   • 检查是否在正确的文件夹运行程序
   • 确认文件夹名称拼写正确
   • 确保文件夹确实存在

👤 问题：人脸识别失败
✅ 解决：
   • 检查照片是否包含清晰人脸
    • 给该学生补 2-3 张清晰正脸参考照（不要多人合照）
   • 使用更高质量的照片
   • 确保照片格式正确

🚫 问题：权限被拒绝
✅ 解决：
   • 关闭其他正在使用文件的程序
   • 检查文件夹权限设置
   • 尝试以管理员身份运行

💾 问题：内存不足
✅ 解决：
   • 关闭其他程序释放内存
   • 减少处理照片数量
   • 重启电脑

📞 获取帮助：
   • 保存错误信息截图
   • 记录具体操作步骤
   • 提供文件结构信息
"""
    }
    
    return guides.get(guide_type, "没有找到相关指南。")

# 全局验证器实例
validator = InputValidator()