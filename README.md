# Jimeng Video Workflow

基于火山引擎 / 即梦 AI 的视频生成工作流。支持文生视频、多段批量生成、自动拼接。

## Features

- 🎬 通过火山引擎 API 调用即梦 Seedance 3.0 Pro 进行视频生成
- 📦 批量多段生成，支持故事级视频制作
- 🔗 ffmpeg 自动拼接多段视频为完整故事片
- 📊 实时进度文件（progress.json）追踪生成状态
- 🔔 Windows 弹窗通知，每段完成自动提醒
- 🔐 火山引擎 AK/SK HMAC-SHA256 签名鉴权

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (用于视频拼接)
- 火山引擎账号 + AccessKey / SecretKey
- 即梦 AI 视频生成服务已开通

## Setup

### 1. 安装 Python 依赖

```bash
pip install requests
```

### 2. 配置环境变量

```bash
# Linux / macOS
export VOLCENGINE_ACCESS_KEY="your_access_key"
export VOLCENGINE_SECRET_KEY="your_secret_key"

# Windows (永久)
setx VOLCENGINE_ACCESS_KEY "your_access_key"
setx VOLCENGINE_SECRET_KEY "your_secret_key"

# OpenClaw 用户推荐写入 ~/.openclaw/.env
```

## Usage

### 单条视频生成

```bash
python jimeng_video_api_minimal.py \
  --title "拈花微笑" \
  --prompt "A cinematic Zen short film..." \
  --aspect-ratio 9:16 \
  --frames 121
```

### 批量多段生成 + 自动拼接

1. 创建分段配置文件（参考 `examples/benlaiwu_yiwu_segments.json`）

2. 运行批量生成并自动拼接：

```bash
python jimeng_batch_runner.py \
  --config examples/benlaiwu_yiwu_segments.json \
  --concat
```

3. 查看进度：打开输出目录下的 `progress.json`

### 手动拼接

```bash
python ffmpeg_concat_jimeng.py \
  --input-dir output_segments_dir \
  --output final_video.mp4
```

## File Structure

```
jimeng-video-workflow/
├── jimeng_video_api_minimal.py   # 核心：单条视频生成 + 火山签名
├── jimeng_batch_runner.py        # 批量生成 + 进度追踪 + 弹窗通知
├── ffmpeg_concat_jimeng.py       # ffmpeg 自动拼接
├── notify_popup.py               # Windows 弹窗通知
├── examples/
│   └── benlaiwu_yiwu_segments.json  # 示例：《本来无一物》四段配置
└── README.md
```

## API Reference

### 火山引擎视频生成 API

- **Host**: `visual.volcengineapi.com`
- **提交任务**: `Action=CVSync2AsyncSubmitTask&Version=2022-08-31`
- **查询结果**: `Action=CVSync2AsyncGetResult&Version=2022-08-31`
- **Region**: `cn-north-1`
- **Service**: `cv`
- **req_key**: `jimeng_ti2v_v30_pro`

### 请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| req_key | string | 能力标识，固定值 |
| prompt | string | 视频描述 |
| image_urls | array | 参考图 URL（可选） |
| aspect_ratio | string | 比例，如 9:16、16:9 |
| frames | int | 帧数 |
| seed | int | 随机种子，-1 为随机 |

## License

MIT
