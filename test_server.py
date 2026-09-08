import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

from server import Handler, PAGES_ORIGIN, run_ffmpeg_transcode


class HealthEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_port}/api/health"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def test_health_endpoint_allows_pages_origin(self):
        request = Request(self.url, headers={"Origin": PAGES_ORIGIN})
        with urlopen(request, timeout=5) as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], PAGES_ORIGIN)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["service"], "m20-audio")
            self.assertTrue(payload["ffmpeg"])


class Reference22TranscodeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "需要 ffmpeg 和 ffprobe")
    def test_reference_22_mode_outputs_fixed_stereo_cbr(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.wav")
            output = os.path.join(tmpdir, "output.mp3")
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:duration=1",
                    source,
                ],
                check=True,
            )

            run_ffmpeg_transcode(
                "ffmpeg",
                source,
                output,
                volume_percent=100,
                mp3_quality=9,
                target_bytes=1,
                requested_sample_rate=0,
                compression_enabled=True,
                reference_22_enabled=True,
            )

            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_name,sample_rate,channels,bit_rate",
                    "-of",
                    "json",
                    output,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            stream = json.loads(probe.stdout)["streams"][0]
            self.assertEqual(stream["codec_name"], "mp3")
            self.assertEqual(stream["sample_rate"], "44100")
            self.assertEqual(stream["channels"], 2)
            self.assertEqual(stream["bit_rate"], "128000")

            packet_sizes = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_packets",
                    "-show_entries",
                    "packet=size",
                    "-of",
                    "csv=p=0",
                    output,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            sizes = {int(line.split(",", 1)[0]) for line in packet_sizes.stdout.splitlines() if line}
            self.assertTrue(sizes.issubset({417, 418}), sizes)


if __name__ == "__main__":
    unittest.main()
