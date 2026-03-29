# Jimeng Video Workflow

基于火山引擎 / 即梦 AI 的视频生成工作流，现已同时支持两条路线：

- **即梦视觉 API / 3.0 Pro 路线**：已打通，适合稳定批量、多段故事片工作流
- **火山方舟 Ark / Seedance 1.5 Pro 路线**：已打通，适合更长单段（如 10-12s）与高质量测试片

## Features

- 🎬 调用即梦视觉 API 生成视频
- 🚀 调用 Ark Seedance 1.5 Pro 生成更长单段视频
- 📦 批量多段生成，支持故事级视频制作
- 🔗 ffmpeg 自动拼接多段视频为完整故事片
- 📊 实时进度文件（progress.json）追踪生成状态
- 🔔 Windows 弹窗通知，每段完成自动提醒
- 🔐 即梦视觉 API：AK/SK HMAC-SHA256 签名鉴权
- 🔑 Ark API：Bearer Token (`ARK_API_KEY`) 鉴权

## Workflows

### 0) 即梦网页会员版自动化

适合：
- 单条试水
- 优先消耗即梦会员积分
- 不走 API 按量计费

核心脚本：
- `jimeng_web_automation.py`

当前能力：
- 自动进入视频生成面板
- 自动填 prompt
- 自动设置比例与时长
- 自动提交生成任务
- 生成状态可写入 `web_progress.json`

### 1) 即梦视觉 API / 3.0 Pro

适合：
- 现有稳定生产线
- 多段故事生成与自动拼接
- 兼容原先已写好的 prompt / batch 流程

核心脚本：
- `jimeng_video_api_minimal.py`
- `jimeng_batch_runner.py`

### 2) Ark Seedance 1.5 Pro

适合：
- 更长单段（如 10-12s）
- 高质量测试片
- 未来升级到更高版本的过渡路径

核心脚本：
- `ark_seedance_video.py`
- `ark_seedance_batch_runner.py`

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (用于视频拼接)
- 火山引擎账号
- 对应视频生成模型已开通

## Environment Variables

### 即梦视觉 API

```bash
VOLCENGINE_ACCESS_KEY=...
VOLCENGINE_SECRET_KEY=...
```

### Ark Seedance 1.5 Pro

```bash
ARK_API_KEY=...
```

> 在这台机器上，推荐长期写入：`C:\Users\Administrator\.openclaw\.env`
> 改完后重启 OpenClaw。

## Usage

### 单条视频生成（即梦网页会员版）

```bash
python jimeng_web_automation.py \
  --prompt "A cinematic Zen short film..." \
  --ratio 9:16 \
  --duration 12s
```

### 单条视频生成（即梦视觉 API）

```bash
python jimeng_video_api_minimal.py \
  --title "拈花微笑" \
  --prompt "A cinematic Zen short film..." \
  --aspect-ratio 9:16 \
  --frames 121
```

### 单条视频生成（Ark Seedance 1.5 Pro）

```bash
python ark_seedance_video.py \
  --model doubao-seedance-1-5-pro-251215 \
  --title "ark-test" \
  --prompt "A cinematic Zen short film..." \
  --ratio 9:16 \
  --duration 12 \
  --resolution 720p \
  --generate-audio
```

### 批量多段生成 + 自动拼接（即梦视觉 API）

```bash
python jimeng_batch_runner.py \
  --config examples/benlaiwu_yiwu_segments.json \
  --concat
```

### 批量多段生成 + 自动拼接（Ark Seedance 1.5 Pro）

```bash
python ark_seedance_batch_runner.py \
  --config examples/benlaiwu_yiwu_ark_segments.json \
  --concat
```

## Progress Tracking

批量生成时，会在输出目录下生成：

- `progress.json`

里面会记录：
- 总段数
- 已完成段数
- 当前正在生成哪一段
- 当前状态（generating / all_segments_done / concat_done）
- 拼接后的最终视频路径

## File Structure

```
jimeng-video-workflow/
├── jimeng_web_automation.py           # 即梦网页会员版：自动进入生成面板、填 prompt、设参数、提交任务
├── jimeng_video_api_minimal.py        # 即梦视觉 API：单条视频生成 + 火山签名
├── jimeng_batch_runner.py             # 即梦视觉 API：批量生成 + 进度追踪 + 弹窗通知
├── ark_seedance_video.py              # Ark Seedance 1.5 Pro：单条视频生成
├── ark_seedance_batch_runner.py       # Ark Seedance 1.5 Pro：批量生成 + 进度追踪 + 弹窗通知
├── ffmpeg_concat_jimeng.py            # ffmpeg 自动拼接
├── notify_popup.py                    # Windows 弹窗通知
├── examples/
│   ├── benlaiwu_yiwu_segments.json        # 即梦视觉 API 示例：《本来无一物》四段
│   └── benlaiwu_yiwu_ark_segments.json    # Ark Seedance 1.5 Pro 示例：《本来无一物》四段
└── README.md
```

## Current Status

### 已打通
- 即梦视觉 API / 3.0 Pro
- Ark Seedance 1.5 Pro
- 多段批量生成
- 自动拼接
- 进度文件与弹窗通知
- GitHub 项目同步

### 待进一步优化
- Seedance 2.0（当前账号仅可体验，不支持 API）
- 双路线效果对比与自动选路
- 更强的项目模板与素材管理

## Repository

- GitHub: https://github.com/LinXingjian365/jimeng-video-workflow

## License

MIT
