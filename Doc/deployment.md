# 部署说明

## 页面

页面部署在 GitHub Pages：

https://jeffery-ho.github.io/AudioOnDeviceEditor/

GitHub Pages 只提供静态页面，音频转码始终由当前电脑上的 Python 服务完成。

## 本机后端

### 推荐启动方式

在任意 Bash 终端执行：

```bash
m20-audio-start
```

服务默认监听：

```text
http://127.0.0.1:8000
```

然后打开 GitHub Pages 页面。页面加载时会请求 `/api/health`；如果服务未启动，页面会先显示启动引导弹窗，连接成功后自动解锁编辑器。

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

浏览器不能从 GitHub Pages 页面直接启动本机进程。如果页面提示服务未启动，请先执行 `m20-audio-start`，再刷新页面。
