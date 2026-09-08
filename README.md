# AudioOnDeviceEditor

Browser audio editor with a local Python and FFmpeg backend.

## Use

1. Start the local backend with `m20-audio-start`.
2. Open the [GitHub Pages editor](https://jeffery-ho.github.io/AudioOnDeviceEditor/).
3. The page checks `http://127.0.0.1:8000/api/health` and shows the local service status.

The browser cannot start local processes by itself. If the page reports that the backend is unavailable, run `m20-audio-start` and refresh the page.
