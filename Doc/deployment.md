# 部署说明

## 页面

页面部署在 GitHub Pages：

https://jeffery-ho.github.io/AudioOnDeviceEditor/

GitHub Pages 提供静态页面，音频转码由 Render 上的 Python/FFmpeg 公网服务完成。

Render 服务地址：

```text
https://audioondeviceeditor.onrender.com
```

健康检查地址：

```text
https://audioondeviceeditor.onrender.com/api/health
```

Render Docker Web Service 监听环境变量 `PORT`，并设置 `HOST=0.0.0.0`；仓库根目录的 `Dockerfile` 负责安装 FFmpeg。免费实例休眠后，页面首次请求可能需要等待冷启动。

后端使用临时目录处理单次上传，不保存用户音频。

## 本机后端（可选，本地开发）

### 推荐启动方式

在任意 Bash 终端执行：

```bash
m20-audio-start
```

服务默认监听：

```text
http://127.0.0.1:8000
```

本机服务只用于本地开发和故障排查，当前 GitHub Pages 页面默认不会请求它。Render 公网服务连接成功后，页面会自动解锁；服务中途休眠或暂时不可用时，会显示冷启动提示并允许重新检测。

### 其他快捷命令

```bash
m20-audio-stop
m20-audio-toggle
```

如果当前终端尚未加载命令定义，重新打开终端，或执行：

```bash
source ~/.bashrc
```

### 图形化启动

双击项目目录中的 `start_server.command`，脚本会启动本机服务并打开 GitHub Pages 页面。服务日志位于：

```text
/tmp/m20_audio_server.log
```

### 健康检查

直接访问以下地址可以确认服务是否运行：

```text
http://127.0.0.1:8000/api/health
```

浏览器不能从 GitHub Pages 页面直接启动本机进程。正式使用不需要启动本机服务；只有本地开发时才执行 `m20-audio-start`。
