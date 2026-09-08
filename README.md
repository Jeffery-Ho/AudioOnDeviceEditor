# AudioOnDeviceEditor

Browser audio editor with a Render-hosted Python and FFmpeg backend.

## Use

1. Open the [GitHub Pages editor](https://jeffery-ho.github.io/AudioOnDeviceEditor/).
2. The page connects to `https://audioondeviceeditor.onrender.com/api/health`.
3. If the free Render instance was sleeping, wait for the cold start and click the check button again.

The backend processes audio in a temporary container and does not persist uploaded files.
