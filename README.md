# JinDing Photography

金鼎的个人摄影作品展示网站，基于 GitHub Pages 构建。

## 技术栈

- 纯 HTML + CSS + JavaScript（无框架）
- Python + Pillow 图片处理
- GitHub Pages 静态托管

## 本地开发

### 安装依赖

```bash
pip install Pillow
```

### 添加新照片

1. 将 JPG 照片放入 `/Users/jinding/Pictures/2025/[主题名]/` 目录
2. 如果主题名是新的，先在 `scripts/process.py` 的 `THEME_DIR_MAP` 中添加映射
3. 运行处理脚本：

```bash
cd JinDing.github.io
python3 scripts/process.py
```

参数说明：
- `--theme "主题名"` — 只处理特定主题
- `--rebuild` — 强制重新生成所有图片
- `--quality 85` — 设置 JPEG 质量

### 发布到 GitHub

```bash
git add .
git commit -m "添加新照片"
git push
```

## 项目结构

```
JinDing.github.io/
├── index.html           # 作品画廊首页
├── about.html           # 关于页面
├── css/style.css        # 样式文件（深色/浅色主题）
├── js/app.js            # 交互逻辑（灯箱、筛选、懒加载）
├── photos/              # 照片资源
│   └── [theme-id]/
│       ├── DSC_0001.JPG # 展示图 1600px
│       └── thumb/       # 缩略图 400px
├── data/
│   ├── photos.json      # 照片元数据
│   └── themes.json      # 主题分类
└── scripts/process.py   # 照片处理脚本
```

## 照片处理说明

- 原始照片自动压缩为 1600px 展示图和 400px 缩略图
- EXIF 信息（拍摄日期、相机、镜头、光圈、快门、ISO）自动提取
- 仅处理 JPG/JPEG 格式，NEF（Nikon RAW）等其他格式会被跳过
