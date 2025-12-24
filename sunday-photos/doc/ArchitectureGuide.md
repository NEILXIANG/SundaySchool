# 开发者架构指南

面向代码贡献者与维护者，深入讲解项目架构设计、核心模块原理与最佳实践。

---

## 一、整体架构

### 1.1 分层设计

```
┌─────────────────────────────────┐
│  CLI 入口 (src/cli/run.py)      │
│  + 兼容层 (src/*.py shim)       │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  ServiceContainer               │
│  (依赖注入容器)                  │
│  - StudentManager               │
│  - FaceRecognizer               │
│  - FileOrganizer                │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Core 核心模块 (src/core/)      │
│  - main.py (主流程编排)          │
│  - face_recognizer.py (识别)    │
│  - student_manager.py (学生)    │
│  - file_organizer.py (文件)     │
│  - config_loader.py (配置)      │
│  - incremental_state.py (快照)  │
│  - recognition_cache.py (缓存)  │
│  - parallel_recognizer.py (并行)│
└─────────────────────────────────┘
```

### 1.3 运行时序（含异常回退）

```
CLI/run.py
  → ServiceContainer.build()
  → SimplePhotoOrganizer.run()
    → initialize()
      → StudentManager.load_students()        # 学生名册/参考照
      → FaceRecognizer.load_reference_encodings()  # 参考编码+缓存
      → FileOrganizer.prepare_output()        # 输出目录准备
    → scan_input_directory()
      → organize_input_by_date()              # 失败→记录警告继续
      → load_snapshot()                       # 失败→空快照
      → compute_incremental_plan()
    → process_photos()
      → load_date_cache()                     # 损坏→忽略缓存
      → parallel_or_serial_recognize()
        并行异常→降级串行（记录fallback）
      → UnknownClustering.run()
      → save_date_cache_atomic()
    → organize_output()
      → FileOrganizer.move_and_copy()         # 单文件失败→跳过+告警
      → create_summary_report()
    → save_snapshot()
```

### 1.2 关键设计原则

**依赖注入（DI）**
- `ServiceContainer` 统一管理核心组件生命周期
- 便于单元测试时 Mock 依赖
- 避免模块间硬编码耦合

**兼容层 (Shim Layer)**
- `src/*.py` 提供向后兼容 API
- 内部委托给 `src/core/` 实现
- 保护老代码免受重构影响

**无感知缓存**
- 识别结果按日期分片缓存在 `output/.state/`
- 参数变化自动失效（params_fingerprint）
- 缓存损坏时静默回退，不影响主流程

**增量处理**
- 快照记录 `input/class_photos` 各日期文件夹状态
- 仅处理新增/变更的日期，跳过已处理
- 删除的日期自动同步清理输出

---

## 二、核心模块详解

### 2.1 ServiceContainer（依赖注入容器）

**位置**: [src/core/main.py](src/core/main.py#L47-L77)

**职责**:
- 集中创建并持有核心组件实例
- 避免循环依赖
- 便于测试时替换 Mock 对象

**使用示例**:
```python
from src.core.main import ServiceContainer

container = ServiceContainer(
    input_dir="input",
    output_dir="output",
    classroom_dir="input/class_photos"
)

# 获取组件
student_mgr = container.get_student_manager()
recognizer = container.get_face_recognizer()

# 传递给主流程
organizer = SimplePhotoOrganizer(service_container=container)
```

**设计要点**:
- 延迟初始化（lazy init）：首次调用 `get_*()` 才创建
- 单例保证：同一 container 多次调用返回同一实例
- 隔离性：不同 container 之间独立

---

### 2.2 增量处理（incremental_state）

**位置**: [src/core/incremental_state.py](src/core/incremental_state.py)

**快照结构**:
```json
{
  "version": 1,
  "generated_at": "2024-01-15T10:30:00",
  "dates": {
    "2024-01-01": {
      "files": [
        {"path": "IMG_001.jpg", "size": 123456, "mtime": 1704067200},
        {"path": "IMG_002.jpg", "size": 234567, "mtime": 1704067300}
      ]
    }
  }
}
```

**核心函数**:
- `build_class_photos_snapshot(dir)`: 构建当前快照
- `load_snapshot(output_dir)`: 加载历史快照
- `save_snapshot(output_dir, snapshot)`: 保存快照
- `compute_incremental_plan(prev, curr)`: 对比生成增量计划

**增量计划结果**:
```python
@dataclass
class IncrementalPlan:
    changed_dates: Set[str]   # 需要重新处理的日期
    deleted_dates: Set[str]   # 需要清理的日期
    snapshot: Dict            # 新快照
```

**流程**:
1. 加载历史快照（首次运行返回 None）
2. 构建当前快照
3. 对比生成增量计划
4. 主流程仅处理 `changed_dates`
5. 清理 `deleted_dates` 对应输出
6. 保存新快照

**设计考量**:
- 0 字节文件自动忽略（`is_supported_nonempty_image_path`）
- 只记录相对路径、size、mtime（整秒），跨平台稳定
- 系统文件自动排除（`.DS_Store`, `Thumbs.db`）

---

### 2.3 识别结果缓存（recognition_cache）

**位置**: [src/core/recognition_cache.py](src/core/recognition_cache.py)

**缓存策略**:
- **分片**: 按日期（YYYY-MM-DD）分文件存储
- **Key**: `rel_path + size + mtime`
- **Value**: `FaceRecognizer.recognize_faces()` 的完整返回
- **失效**: `params_fingerprint` 变化时整体失效

**缓存结构**:
```json
{
  "version": 1,
  "date": "2024-01-01",
  "params_fingerprint": "sha256:abc123...",
  "entries": {
    "IMG_001.jpg|123456|1704067200": {
      "status": "success",
      "recognized_students": ["张三", "李四"],
      "total_faces": 2
    }
  }
}
```

**核心函数**:
- `load_date_cache(output_dir, date)`: 加载某日期缓存
- `save_date_cache_atomic(output_dir, date, cache)`: 原子保存
- `compute_params_fingerprint(params)`: 计算参数指纹

**使用示例**:
```python
from src.core.recognition_cache import (
    load_date_cache,
    save_date_cache_atomic,
    compute_params_fingerprint
)

params = {"tolerance": 0.6, "min_face_size": 50}
fingerprint = compute_params_fingerprint(params)

cache = load_date_cache(output_dir, "2024-01-01")

# 检查指纹是否匹配
if cache.get("params_fingerprint") != fingerprint:
    cache = {"version": 1, "date": "2024-01-01", 
             "params_fingerprint": fingerprint, "entries": {}}

# 查询缓存
key = f"{rel_path}|{size}|{mtime}"
if key in cache["entries"]:
    result = cache["entries"][key]
else:
    result = recognizer.recognize_faces(photo_path, return_details=True)
    cache["entries"][key] = result

save_date_cache_atomic(output_dir, "2024-01-01", cache)
```

**容错设计**:
- JSON 损坏时返回空缓存，不抛异常
- 原子写入（tmp → rename）防止写入中断
- 缓存不命中时静默回退到实时识别

---

### 2.4 智能并行识别（parallel_recognizer）

**位置**: [src/core/parallel_recognizer.py](src/core/parallel_recognizer.py)

**决策逻辑**:
1. **强制禁用**: `SUNDAY_PHOTOS_NO_PARALLEL=1` → 串行
2. **强制启用**: `SUNDAY_PHOTOS_PARALLEL=1` → 并行（如果 ≥30 张）
3. **配置文件**: `config.json` 中 `parallel_recognition.enabled`
4. **智能提示**: ≥50 张时提示可加速

**核心函数**:
- `init_worker()`: 子进程初始化器（缓存已知编码）
- `recognize_one(image_path)`: 子进程识别单张照片
- `_truthy_env(name, default)`: 解析环境变量为布尔值

**使用示例**:
```python
from multiprocessing import Pool
from src.core.parallel_recognizer import init_worker, recognize_one

# 准备参数
known_encodings = [...]
known_names = ["张三", "李四"]
tolerance = 0.6
min_face_size = 50

# 创建进程池
with Pool(
    processes=4,
    initializer=init_worker,
    initargs=(known_encodings, known_names, tolerance, min_face_size)
) as pool:
    results = pool.map(recognize_one, photo_paths, chunksize=12)

# 结果格式：[(path1, details1), (path2, details2), ...]

  ### 2.5 异常与错误语义（跨模块约定）

  - **输入/输出类错误**：目录不存在、无写权限 → 向上抛出异常，由 CLI 捕获并输出面向老师的提示；记录致命 error 日志。
  - **单文件/单日期故障**：图片损坏、单日快照损坏 → 记录 warning，跳过当前文件/日期，继续其他任务。
  - **并行失败**：自动降级串行，记录 fallback 原因（如 OOM/超时/worker 异常），不终止主流程。
  - **缓存/快照损坏**：忽略损坏内容并重建空结构（cache/snapshot），记录 warning。
  - **外部依赖异常**（face_recognition/dlib）：记录 error 并继续处理其他照片；必要时标记该照片为未识别。
  - **日志要求**：所有错误需写明发生位置（模块/函数）、受影响的路径（如有）、下一步建议（如“补充参考照”/“检查权限”）。
```

**优化要点**:
- `initializer` 在子进程中缓存只读数据，避免每次传递
- `chunksize` 平衡任务分发开销与负载均衡
- 异常时自动回退串行（try-except 包裹）

**性能数据**:
- 小批量 (< 30 张): 串行更快（避免进程启动开销）
- 中等批量 (30-100 张): 并行通常可明显加速（效果取决于机器与照片规模）
- 大批量 (100+ 张): 并行通常可进一步受益（效果取决于机器与照片规模）

---

### 2.5 配置加载器（config_loader）

**位置**: [src/core/config_loader.py](src/core/config_loader.py)

**优先级**:
```
环境变量 (SUNDAY_PHOTOS_NO_PARALLEL) 
  ↓
环境变量 (SUNDAY_PHOTOS_PARALLEL)
  ↓
config.json
  ↓
DEFAULT_CONFIG (src/core/config.py)
```

**核心方法**:
- `load_config()`: 加载配置（带环境变量覆盖）
- `get(key, default)`: 获取配置项
- `save_config()`: 保存配置
- `update(key, value)`: 更新配置

**使用示例**:
```python
from src.core.config_loader import ConfigLoader

loader = ConfigLoader()
tolerance = loader.get("tolerance", 0.6)

# 更新配置
loader.update("tolerance", 0.5)
loader.save_config()

# 路径解析
input_dir = loader.resolve_path("input_dir")
```

**特殊处理**:
- 并行识别配置合并（环境变量优先）
- 路径自动解析（相对 → 绝对）
- 缺失配置项使用默认值

---

## 三、开发最佳实践

### 3.1 单元测试规范

**测试文件命名**:
- 完整测试: `test_<module>_complete.py`
- 集成测试: `test_<feature>_integration.py`
- 边界测试: `test_<module>_edge_cases.py`

**测试类组织**:
```python
class TestModuleName:
    """模块功能测试"""
    
    def test_basic_functionality(self):
        """基础功能应该正常工作"""
        pass
    
    def test_edge_case_empty_input(self):
        """空输入应该返回默认值"""
        pass
    
    def test_error_handling(self):
        """错误应该被正确捕获"""
        pass
```

**Mock 使用**:
```python
from unittest.mock import patch, MagicMock

@patch('face_recognition.load_image_file')
def test_with_mock(mock_load):
    mock_load.return_value = MagicMock()
    # 测试代码
```

---

### 3.2 日志规范（见任务4统一整理）

**层级定义**:
- **DEBUG**: 详细调试信息（人脸位置、编码距离）
- **INFO**: 关键流程节点（开始识别、完成整理）
- **WARNING**: 可恢复的异常（缺少参考照片、人脸过小）
- **ERROR**: 用户需要关注的错误（文件损坏、权限不足）

**格式规范**:
```python
logger.info("[步骤 1/4] 正在初始化系统组件...")
logger.info(f"✓ 本次需要处理 {count} 张照片")
logger.warning(f"警告: 有 {n} 名学生缺少参考照片")
logger.error(f"输入目录不存在: {path}")
logger.debug(f"识别到: {photo} -> {names}")
```

---

### 3.3 错误处理原则

**分层处理**:
1. **底层**: 具体异常（FileNotFoundError, ValueError）
2. **中层**: 业务异常（StudentPhotosLayoutError）
3. **顶层**: 统一捕获，记录日志，友好提示

**示例**:
```python
try:
    result = recognizer.recognize_faces(photo_path)
except FileNotFoundError:
    logger.error(f"文件不存在: {photo_path}")
    return {"status": "file_not_found"}
except Exception as e:
    logger.error(f"识别失败: {photo_path}, 错误: {e}")
    return {"status": "error", "message": str(e)}
```

**用户友好提示**:
- 避免技术术语（"dlib assertion failed" → "人脸检测失败"）
- 提供可操作建议（"请检查照片是否损坏"）
- 记录详细日志供排查

---

## 四、架构决策记录（ADR）

### ADR-001: 为何选择依赖注入容器？

**背景**: 模块间依赖复杂，测试时难以 Mock

**决策**: 引入 `ServiceContainer` 统一管理组件

**优点**:
- 测试时可替换 Mock 对象
- 避免循环依赖
- 单一职责（创建与使用分离）

**缺点**:
- 增加一层抽象
- 新手可能不熟悉 DI 模式

**结论**: 利大于弊，采用 DI 容器

---

### ADR-002: 为何按日期分片缓存？

**背景**: 单文件缓存会随照片增加而膨胀

**决策**: 按日期（YYYY-MM-DD）分片存储

**优点**:
- 删除日期时自动清理对应缓存
- 单个缓存文件较小，读写快
- 与增量处理策略对齐

**缺点**:
- 多个缓存文件管理
- 需要手动清理过期日期

**结论**: 分片策略更适合长期使用

---

### ADR-003: 为何默认禁用并行识别？

**背景**: 并行识别在低配机器可能失败

**决策**: 默认 `enabled: false`，提供环境变量快速启用

**优点**:
- 兼容低内存环境
- 避免新手困惑
- 提供智能提示引导启用

**缺点**:
- 大批量场景初次使用较慢

**结论**: 稳定性优先，通过提示教育用户

---

## 五、常见开发任务

### 5.1 添加新配置项

1. 在 [src/core/config.py](src/core/config.py) 添加默认值
2. 更新 `DEFAULT_CONFIG` 字典
3. 在 `config_loader.py` 处理特殊逻辑（如有）
4. 更新 [doc/CONFIG.md](doc/CONFIG.md) 文档
5. 添加单元测试到 `test_config_loader_complete.py`

### 5.2 优化识别算法

1. 在 [src/core/face_recognizer.py](src/core/face_recognizer.py) 修改
2. 更新 `params_fingerprint` 计算（如参数变化）
3. 运行完整测试确保兼容性
4. 更新性能数据到文档

### 5.3 添加新的缓存策略

1. 参考 `recognition_cache.py` 设计接口
2. 实现 load/save/compute_key 方法
3. 集成到主流程 `main.py`
4. 添加单元测试与集成测试
5. 更新架构文档

---

## 六、性能优化指南

### 6.1 识别性能

**瓶颈**:
- `face_recognition.face_encodings()` (CPU 密集)
- `face_recognition.compare_faces()` (距离计算)

**优化方向**:
- 启用并行识别（多核机器通常更快；以实际运行结果为准）
- 缩小参考照片尺寸（加快编码）
- 减少 `tolerance` 减少比对次数

### 6.2 内存优化

**注意事项**:
- 避免一次性加载所有照片
- 及时释放 numpy 数组
- 限制并行进程数（workers ≤ CPU 核心数）

**示例**:
```python
# 避免
all_images = [load_image(p) for p in paths]  # 占用大量内存

# 推荐
for path in paths:
    image = load_image(path)
    process(image)
    del image  # 及时释放
```

### 6.3 磁盘 I/O 优化

**策略**:
- 使用缓存减少重复识别
- 批量写入（`shutil.copy2` 比多次小写入快）
- 原子写入防止损坏（tmp → rename）

---

## 七、调试技巧

### 7.1 启用详细日志

```bash
# 方法1: 环境变量
export LOG_LEVEL=DEBUG
python src/cli/run.py

# 方法2: 代码修改
logger.setLevel(logging.DEBUG)
```

### 7.2 单独测试某模块

```bash
# 测试配置加载
python3 -m pytest tests/test_config_loader_complete.py -v

# 测试识别器
python3 -m pytest tests/test_face_recognizer_extra.py -v

# 测试增量处理
python3 -m pytest tests/test_incremental_state_complete.py -v
```

### 7.3 打印中间结果

```python
# 在 face_recognizer.py 添加调试打印
def recognize_faces(self, photo_path):
    encodings = face_recognition.face_encodings(image)
    print(f"DEBUG: 检测到 {len(encodings)} 个人脸")  # 临时调试
    ...
```

---

## 八、贡献流程

1. **Fork** 项目到个人仓库
2. **创建分支**: `git checkout -b feature/new-feature`
3. **开发**: 编写代码 + 单元测试
4. **测试**: `python3 -m pytest -v`
5. **提交**: 清晰的 commit message
6. **Pull Request**: 描述变更内容与动机
7. **代码审查**: 响应反馈，修改代码
8. **合并**: 维护者审核通过后合并

---

## 九、参考资料

- [face_recognition 文档](https://face-recognition.readthedocs.io/)
- [dlib 性能优化](http://dlib.net/optimization.html)
- [PyInstaller 打包指南](https://pyinstaller.org/en/stable/)
- [Python 并发编程](https://docs.python.org/3/library/multiprocessing.html)

---

**更新记录**:
- 2024-01-15: 初始版本，覆盖核心架构与模块详解
