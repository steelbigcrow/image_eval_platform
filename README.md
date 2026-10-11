# image_eval_platform

图片比对平台：上传「原图片」与「目标图片」，输出相似度评估结果。

- **后端**：Python + Flask，提供上传校验与比对接口
- **前端**：Jinja2 模板 + 原生 HTML/CSS/JS，无需 Node 构建
- **比对算法**：可插拔注册表，当前为三个**占位实现**，后续可逐个替换为正式算法

## 快速开始

```bash
# 1. 安装依赖
python -m pip install -r requirements.txt

# 2. 启动服务（默认开启调试与热重载）
python app.py

# 3. 浏览器打开
#    http://127.0.0.1:5000
```

## 项目结构

```
image_eval_platform/
├── app.py                    # Flask 应用与路由
├── config.py                 # 集中配置（可用环境变量覆盖）
├── comparators/              # 比对算法层
│   ├── base.py               #   BaseComparator 抽象基类 + ComparisonResult
│   ├── registry.py           #   注册表：register / get / list_all
│   ├── histogram.py          #   颜色直方图（占位）
│   ├── pixel.py              #   逐像素 RMSE（占位）
│   └── ahash.py              #   感知哈希（占位）
├── imaging/
│   └── processor.py          # 上传校验、EXIF 方向修正、RGB 归一、预览生成
├── templates/
│   └── index.html            # 单页界面
├── static/
│   ├── css/style.css
│   └── js/app.js
└── tests/
    └── test_compare.py       # pytest 接口与算法测试
```

## 接口说明

### `GET /api/algorithms`

返回已注册算法列表，前端据此渲染下拉框。

```json
{
  "ok": true,
  "data": {
    "algorithms": [
      {
        "key": "histogram",
        "label": "颜色直方图（占位）",
        "description": "比较 HSV 颜色分布，忽略构图与空间位置，用于快速初筛。"
      }
    ]
  }
}
```

### `POST /api/compare`

`multipart/form-data` 表单：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source` | file | 是 | 原图片 |
| `target` | file | 是 | 目标图片 |
| `algorithm` | string | 否 | 算法 key，缺省用 `histogram` |

成功响应：

```json
{
  "ok": true,
  "data": {
    "algorithm": { "key": "histogram", "label": "...", "description": "..." },
    "score": 92.31,
    "level": "高度相似",
    "metrics": { "histogram_iou": 0.9231, "histogram_cosine": 0.9912 },
    "message": "颜色分布相似度，不反映空间布局，仅作占位参考。",
    "source": { "filename": "a.png", "width": 640, "height": 480, "mode": "RGB", "preview": "data:image/png;base64,..." },
    "target": { "filename": "b.png", "width": 640, "height": 480, "mode": "RGB", "preview": "data:image/png;base64,..." },
    "created_at": "2026-10-11T08:40:00+00:00"
  }
}
```

失败响应统一为 `{"ok": false, "message": "原因"}`，状态码 400 / 413 / 500。

`level` 由 `score` 分档：≥90 高度相似、≥75 较为相似、≥50 差异明显、否则差异很大。

## 当前算法（均为占位实现）

| key | 算法 | 思路 | 已知局限 |
| --- | --- | --- | --- |
| `histogram` | 颜色直方图 | HSV 的 H-S 联合直方图，取交集/并集 | 忽略空间布局，构图不同也可能高分 |
| `pixel` | 逐像素 RMSE | 统一缩放到 256×256 后算 RMSE 推导分数 | 对裁剪、位移、缩放极度敏感 |
| `ahash` | 感知哈希 | 8×8 平均哈希 + 汉明距离 | 粒度粗，只能判断粗略重复 |

这些实现只用于打通链路，**不代表最终效果**。

## 新增/替换算法

算法层与前后端完全解耦，替换算法不需要改动 `app.py`、模板或 JS：

1. 在 `comparators/` 下新建模块，继承 `BaseComparator`：

```python
from comparators.base import BaseComparator, ComparisonResult
from comparators.registry import register

@register
class MyComparator(BaseComparator):
    key = "my_algo"          # 接口唯一标识
    label = "我的算法"        # 下拉框显示名
    description = "一句话说明"

    def compare(self, source, target):
        # source / target 均为已转 RGB 的 PIL.Image
        score = 88.5
        return ComparisonResult.from_score(
            score,
            metrics={"my_metric": 0.885},   # 原样透传给前端展示
            message="补充说明",
        )
```

2. 在 `comparators/__init__.py` 导入该模块（导入即注册）：

```python
from comparators import ahash, histogram, pixel, my_algo  # noqa: F401
```

3. 重启服务，前端下拉框会自动出现新算法。

约定：

- `score` 必须归一化到 `0~100`，越大越相似；`ComparisonResult.from_score` 会自动裁剪越界值。
- `metrics` 放可解释的中间量，方便调参和排查。
- 算法内部若需要预热（加载模型、读权重等），可在 `compare()` 内做进程内缓存，避免每次请求重复加载。

后续可考虑的算法方向：结构相似度 SSIM、多尺度特征比对（OpenCV / DNN embedding）、局部特征匹配（ORB + RANSAC）、深度学习感知度量 LPIPS / DINOv2。

## 图片处理约定

进入算法前，所有图片都已完成：

- 按扩展名白名单校验（png/jpg/jpeg/bmp/gif/webp/tif/tiff）
- 修正手机照片的 EXIF 方向
- 透明通道按白底合成，统一转为 `RGB`
- 另生成最长边 960 的 base64 预览图，仅用于界面展示，**不参与比对**

请求体上限默认 20 MB，由环境变量 `APP_MAX_UPLOAD_MB` 控制。

## 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | 监听地址 |
| `APP_PORT` | `5000` | 监听端口 |
| `APP_DEBUG` | `1` | 调试模式 |
| `APP_RELOADER` | 跟随 `APP_DEBUG` | 热重载 |
| `APP_MAX_UPLOAD_MB` | `20` | 单次请求上传体积上限 |

生产部署示例：

```bash
set APP_DEBUG=0
set APP_RELOADER=0
python app.py
```

或使用正式 WSGI 服务器：

```bash
python -m pip install waitress
waitress-serve --port=5000 app:app
```

## 测试

```bash
python -m pytest -q
```

覆盖：算法注册、相同图高分、差异图低分、三种算法均能通过接口调用、缺文件 / 未知算法 / 不支持格式 / 损坏文件等错误分支、JPEG 与透明 PNG 支持。
