# 部署说明

## 页面

页面部署在 GitHub Pages：

https://jeffery-ho.github.io/AudioOnDeviceEditor/

## 本机后端

GitHub Pages 只提供静态页面。公网部署完成后，页面会优先使用公网 Docker 后端；公网不可用时回退到本机后端。

### Docker 本机运行

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

容器只绑定到本机 `127.0.0.1:8000`，并配置为异常退出后自动重启。

### Hugging Face Docker Space

Space 需要使用公开 Docker Space，并将 `server.py`、`index.html`、`backend-config.js`、`Dockerfile`、`.dockerignore` 和本文件所需的 Space README 配置上传到 Space 仓库。

Space 的运行端口为 `7860`，容器使用 `HOST=0.0.0.0`。

创建 Space 后，将公网地址写入 `backend-config.js`：

```javascript
window.AUDIO_EDITOR_PUBLIC_BACKEND_URL = "https://<namespace>-audio-on-device-editor.hf.space";
```

然后提交并推送 GitHub Pages 前端。页面会先请求这个公网地址，失败后再请求 `http://127.0.0.1:8000`。

在项目目录执行：

```bash
python3 server.py
```

然后打开 GitHub Pages 页面。页面在该域名下会自动请求 `http://127.0.0.1:8000`；直接通过本机地址访问时，仍使用同源后端接口。

如果浏览器提示无法连接后端，请确认本机服务正在运行，并使用 `http://127.0.0.1:8000` 检查服务状态。
