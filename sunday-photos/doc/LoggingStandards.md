# 日志规范指南

统一的日志使用规范，确保日志信息清晰、一致且易于排查问题。

---

## 一、日志层级定义

### 1.1 DEBUG（调试）

**用途**: 详细的调试信息，仅供开发者排查问题使用

**使用场景**:
- 识别结果详情（人脸位置、编码距离）
- 缓存命中/未命中详情
- 文件路径解析过程
- 循环内部状态
- 函数参数与返回值

**示例**:
```python
logger.debug(f"识别到: {os.path.basename(photo_path)} -> {student_names}")
logger.debug(f"无人脸: {os.path.basename(photo_path)}")
logger.debug(f"复制照片: {source_path} -> {target_path}")
logger.debug(f"在图片中未检测到人脸: {image_path}")
logger.debug(f"持久化编码失败（不影响当前会话）: {e}")
```

**注意事项**:
- 默认不输出到控制台（需设置 LOG_LEVEL=DEBUG）
- 可包含敏感路径信息
- 避免过度使用（影响性能）

---

### 1.2 INFO（信息）

**用途**: 关键流程节点与正常状态信息，面向用户

**使用场景**:
- 程序启动/结束横幅
- 步骤进度提示（[步骤 1/4]）
- 操作完成确认（✓ 标记）
- 统计数据（处理张数、成功数）
- 性能提示与建议
- 配置加载成功

**示例**:
```python
logger.info("=====================================")
logger.info("主日学课堂照片自动整理工具（文件夹模式）")
logger.info("[步骤 1/4] 正在初始化系统组件...")
logger.info("✓ 系统组件初始化完成")
logger.info(f"✓ 本次需要处理 {len(photo_files)} 张照片")
logger.info(f"成功加载 {len(self.students_data)} 名学生信息")
logger.info("💡 性能提示：检测到 %d 张待识别照片，建议开启并行识别以加速处理", photo_count)
logger.info(f"总耗时: {int(minutes)}分{int(seconds)}秒")
```

**格式规范**:
- 步骤提示: `[步骤 X/Y] 正在...`
- 完成确认: `✓ 操作描述已完成`
- 统计信息: `关键词: 数值 单位`
- 提示信息: `💡/ℹ️  建议内容`

**用户友好原则**:
- 使用中文描述
- 避免技术术语
- 提供可操作建议
- 数据易于理解

---

### 1.3 WARNING（警告）

**用途**: 可恢复的异常或需要用户关注的情况

**使用场景**:
- 缺少参考照片
- 人脸过小无法识别
- 文件损坏但可继续
- 空文件尝试读取
- 并行识别失败回退串行
- 配置异常使用默认值

**示例**:
```python
logger.warning(f"警告: 有 {len(missing_photos)} 名学生缺少参考照片")
logger.warning(f"学生 {student_name} 没有参考照片")
logger.warning(f"在照片中未检测到人脸: {photo_path}")
logger.warning(f"student_photos目录不存在: {self.students_photos_dir}")
logger.warning(f"并行识别失败，将回退串行识别: {str(e)}")
logger.warning("⚠️ 输入目录为空或不存在，请检查 input/student_photos 文件夹。")
```

**格式规范**:
- 开头使用 `警告:`/`⚠️` 标记
- 清晰描述问题
- 说明影响范围
- 提示用户检查路径

**处理原则**:
- 不中断程序执行
- 记录详细信息供排查
- 必要时提供解决建议

---

### 1.4 ERROR（错误）

**用途**: 用户需要关注的错误，可能影响结果

**使用场景**:
- 输入目录不存在
- 文件权限不足
- 照片加载失败
- 复制操作失败
- 识别严重错误
- 配置文件损坏

**示例**:
```python
logger.error(f"输入目录不存在: {self.photos_dir}")
logger.error(f"复制照片失败: {photo_path} -> {student_dir}")
logger.error(f"加载学生 {student_name} 的照片 {photo_path} 失败: {str(e)}")
logger.error(f"识别出错: {os.path.basename(photo_path)} - {msg}")
logger.error(f"新照片不存在: {new_photo_path}")
```

**格式规范**:
- 明确说明错误类型
- 包含相关路径/文件名
- 附带异常信息
- 不使用过于技术的术语

**用户友好转换**:
```python
# 避免
logger.error(f"dlib assertion failed: {e}")

# 推荐
logger.error(f"人脸检测失败: {photo_path}，请检查照片是否损坏")
```

---

### 1.5 CRITICAL（严重）

**用途**: 导致程序无法继续的致命错误

**使用场景**:
- 核心依赖库缺失
- 内存不足无法继续
- 数据库连接失败（如有）
- 系统资源耗尽

**注意**: 当前项目中较少使用，大部分错误可恢复

**示例**:
```python
logger.critical("无法加载 face_recognition 库，程序无法继续")
logger.critical("磁盘空间不足，无法保存输出文件")
```

---

## 二、日志格式规范

### 2.1 基础格式

**配置**:
```python
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**输出示例**:
```
2024-01-15 10:30:45 - main - INFO - [步骤 1/4] 正在初始化系统组件...
2024-01-15 10:30:46 - student_manager - WARNING - 警告: 有 2 名学生缺少参考照片
```

### 2.2 特殊标记使用

**进度步骤**:
```python
logger.info("[步骤 1/4] 正在初始化系统组件...")
logger.info("[步骤 2/4] 正在扫描输入目录...")
logger.info("[步骤 3/4] 正在进行人脸识别...")
logger.info("[步骤 4/4] 正在整理照片...")
```

**完成确认**:
```python
logger.info("✓ 系统组件初始化完成")
logger.info("✓ 照片整理完成")
logger.info("✓ 本次需要处理 50 张照片")
```

**提示信息**:
```python
logger.info("💡 性能提示：建议开启并行识别以加速处理")
logger.info("ℹ️  照片数量 < 并行阈值，使用串行模式")
logger.warning("⚠️ 输入目录为空或不存在")
```

**横幅分隔**:
```python
logger.info("=====================================")
logger.info("主日学课堂照片自动整理工具")
logger.info("=====================================")
```

---

## 三、模块化日志实践

### 3.1 获取Logger

**推荐方式**:
```python
import logging

logger = logging.getLogger(__name__)
```

**避免**:
```python
# 不要使用根logger
logger = logging.getLogger()

# 不要硬编码模块名
logger = logging.getLogger("face_recognizer")
```

### 3.2 Logger命名规范

- `src.core.main` → 主流程日志
- `src.core.face_recognizer` → 识别模块日志
- `src.core.student_manager` → 学生管理日志
- `src.core.file_organizer` → 文件整理日志

### 3.3 日志配置初始化

**位置**: [src/core/utils.py](src/core/utils.py)

**使用**:
```python
from src.core.utils import setup_logger

logger = setup_logger("main", log_dir="logs")
```

---

## 四、异常日志规范

### 4.1 记录异常堆栈

**推荐**:
```python
try:
    result = process_photo(path)
except Exception as e:
    logger.error(f"处理照片失败: {path}", exc_info=True)
    # 或
    logger.debug("详细堆栈信息", exc_info=True)
```

**避免**:
```python
# 不要吞掉异常
try:
    process_photo(path)
except Exception:
    pass  # ❌ 静默失败

# 不要只打印异常对象
except Exception as e:
    logger.error(e)  # ❌ 缺少上下文
```

### 4.2 分层处理

**底层**: 记录详细堆栈（DEBUG）
```python
except FileNotFoundError as e:
    logger.debug(f"文件读取失败: {path}", exc_info=True)
    return None
```

**中层**: 记录业务错误（WARNING/ERROR）
```python
except StudentPhotosLayoutError as e:
    logger.warning(f"学生照片目录结构异常: {e}")
    return default_value
```

**顶层**: 用户友好提示（ERROR）
```python
except Exception as e:
    logger.error(f"照片整理失败，请检查输入目录: {input_dir}")
    sys.exit(1)
```

---

## 五、性能与调试

### 5.1 条件日志

**避免过度计算**:
```python
# 推荐
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = compute_detailed_stats()
    logger.debug(f"详细统计: {expensive_debug_info}")

# 避免
logger.debug(f"详细统计: {compute_detailed_stats()}")  # 即使不输出也会计算
```

### 5.2 批量操作日志

**循环内谨慎使用INFO**:
```python
# 避免
for photo in photos:
    logger.info(f"处理照片: {photo}")  # ❌ 大量输出

# 推荐
for photo in photos:
    logger.debug(f"处理照片: {photo}")  # ✓ DEBUG级别

logger.info(f"✓ 已处理 {len(photos)} 张照片")  # ✓ 汇总信息
```

### 5.3 调试开关

**环境变量控制**:
```bash
export LOG_LEVEL=DEBUG
python src/cli/run.py
```

**代码控制**:
```python
if os.environ.get("DEBUG_MODE") == "1":
    logger.setLevel(logging.DEBUG)
```

---

## 六、日志文件管理

### 6.1 日志轮转配置

**当前配置**:
```python
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

**轮转策略**:
- 单文件最大 10MB
- 保留最近 5 个备份
- 自动删除过期日志

### 6.2 日志文件命名

**格式**: `photo_organizer_YYYYMMDD.log`

**示例**:
```
logs/photo_organizer_20240115.log
logs/photo_organizer_20240115.log.1
logs/photo_organizer_20240115.log.2
```

---

## 七、代码审查检查清单

### 7.1 日志层级检查

- [ ] INFO 用于关键流程，非循环内部
- [ ] WARNING 用于可恢复异常
- [ ] ERROR 用于需要用户关注的问题
- [ ] DEBUG 用于详细调试信息
- [ ] 避免在循环中使用 INFO

### 7.2 用户友好检查

- [ ] 中文描述清晰
- [ ] 避免技术术语
- [ ] 路径使用相对路径显示
- [ ] 错误提示包含解决建议

### 7.3 性能检查

- [ ] 大计算量日志使用 isEnabledFor
- [ ] 循环内使用 DEBUG
- [ ] 批量操作使用汇总日志

### 7.4 异常处理检查

- [ ] 关键异常记录堆栈
- [ ] 底层 DEBUG，顶层 ERROR
- [ ] 不吞掉异常
- [ ] 友好转换技术错误

---

## 八、常见问题

### Q1: 何时使用 DEBUG vs INFO？

**规则**: 用户关心 → INFO；开发者关心 → DEBUG

**示例**:
```python
# 用户关心处理了多少张照片
logger.info(f"✓ 已处理 {count} 张照片")  # INFO

# 开发者关心具体识别了哪张照片
logger.debug(f"识别到: {photo} -> {names}")  # DEBUG
```

### Q2: 如何记录敏感信息？

**原则**: 敏感信息仅记录到 DEBUG 级别

**示例**:
```python
# 完整路径可能包含用户名
logger.debug(f"完整路径: {os.path.abspath(path)}")  # DEBUG

# 用户看到的只有文件名
logger.info(f"处理文件: {os.path.basename(path)}")  # INFO
```

### Q3: 循环中如何正确记录日志？

**推荐模式**:
```python
logger.info(f"[步骤 3/4] 正在进行人脸识别...")

for photo in photos:
    logger.debug(f"识别: {photo}")  # DEBUG
    result = recognize(photo)

logger.info(f"✓ 人脸识别完成")  # INFO汇总
logger.info(f"  - 识别成功: {success_count} 张")
logger.info(f"  - 识别失败: {failed_count} 张")
```

---

## 九、快速参考

| 层级 | 使用场景 | 示例前缀 | 默认输出 |
|------|---------|---------|---------|
| DEBUG | 详细调试 | `识别到:` | 否 |
| INFO | 关键流程 | `[步骤 X/Y]` `✓` | 是 |
| WARNING | 可恢复异常 | `警告:` `⚠️` | 是 |
| ERROR | 用户需关注 | `错误:` | 是 |
| CRITICAL | 致命错误 | `严重:` | 是 |

---

## 十、更新记录

- 2024-01-15: 初始版本，统一日志规范
