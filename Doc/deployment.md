# 部署说明

## 页面

页面部署在 GitHub Pages：

https://jeffery-ho.github.io/AudioOnDeviceEditor/

## 本机后端

GitHub Pages 只提供静态页面，音频转码仍由本机的 `server.py` 和 FFmpeg 完成。

在项目目录执行：

```bash
python3 server.py
```

然后打开 GitHub Pages 页面。页面在该域名下会自动请求 `http://127.0.0.1:8000`；直接通过本机地址访问时，仍使用同源后端接口。

如果浏览器提示无法连接后端，请确认本机服务正在运行，并使用 `http://127.0.0.1:8000` 检查服务状态。
