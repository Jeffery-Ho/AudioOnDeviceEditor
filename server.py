#!/usr/bin/env python3
import glob
import http.server
import os
import re
import shutil
import subprocess
import tempfile
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
PAGES_ORIGIN = "https://jeffery-ho.github.io"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))
BITRATE_LADDER = [320, 256, 224, 192, 160, 128, 112, 96, 80, 64, 56, 48, 40, 32, 24, 16]


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def quality_to_kbps(mp3_quality: int) -> int:
    # LAME VBR质量近似目标码率，仅用于fallback编码器
    table = {
        0: 320,
        1: 256,
        2: 192,
        3: 175,
        4: 160,
        5: 130,
        6: 112,
        7: 96,
        8: 80,
        9: 64,
    }
    return table.get(mp3_quality, 192)


def parse_duration_seconds(ffmpeg_stderr: str) -> float:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", ffmpeg_stderr)
    if not match:
        return 0.0
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def probe_duration_seconds(ffmpeg_bin: str, in_path: str) -> float:
    result = subprocess.run(
        [ffmpeg_bin, "-i", in_path],
        capture_output=True,
        text=True,
    )
    return parse_duration_seconds(result.stderr)


def estimate_target_kbps(target_bytes: int, duration_seconds: float) -> int:
    if duration_seconds <= 0:
        return 128
    # 预留少量容器/帧开销，避免估算过于激进导致超出目标。
    usable_bits = max(1, int(target_bytes * 8 * 0.96))
    return max(16, int(usable_bits / duration_seconds / 1000))


def choose_sample_rates(target_kbps: int):
    if target_kbps <= 24:
        return [12000, 11025, 8000, 16000]
    if target_kbps <= 40:
        return [16000, 12000, 22050, 11025]
    if target_kbps <= 64:
        return [22050, 16000, 24000, 32000]
    if target_kbps <= 96:
        return [32000, 24000, 22050, 44100]
    return [44100, 32000, 48000, 24000]


def choose_bitrates(mp3_quality: int, target_bytes: int, duration_seconds: float):
    quality_cap = quality_to_kbps(mp3_quality)
    target_kbps = min(quality_cap, estimate_target_kbps(target_bytes, duration_seconds))
    lower_or_equal = [x for x in BITRATE_LADDER if x <= target_kbps]
    higher = [x for x in BITRATE_LADDER if x > target_kbps]
    # 优先从估算值附近向下尝试，只有在必要时再向上回退。
    ordered = lower_or_equal + list(reversed(higher))
    return ordered[:5] if ordered else [quality_cap]


def resolve_ffmpeg_binary() -> str:
    env_path = os.environ.get("FFMPEG_BIN")
    if env_path:
        # 支持两种写法：
        # 1) FFMPEG_BIN=/abs/path/to/ffmpeg
        # 2) FFMPEG_BIN=/abs/path/to/FFMPEG_BIN   (目录内含 ffmpeg)
        if os.path.isfile(env_path):
            return env_path
        if os.path.isdir(env_path):
            candidate = os.path.join(env_path, "ffmpeg")
            if os.path.isfile(candidate):
                return candidate
            candidate_exe = os.path.join(env_path, "ffmpeg.exe")
            if os.path.isfile(candidate_exe):
                return candidate_exe

    path_bin = shutil.which("ffmpeg")
    if path_bin:
        return path_bin

    project_bin = os.path.join(os.path.dirname(__file__), "FFMPEG_BIN", "ffmpeg")
    if os.path.isfile(project_bin):
        return project_bin
    project_bin_exe = os.path.join(os.path.dirname(__file__), "FFMPEG_BIN", "ffmpeg.exe")
    if os.path.isfile(project_bin_exe):
        return project_bin_exe

    local_bins = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "ffmpeg-local-*", "bin", "ffmpeg")))
    if local_bins:
        return local_bins[-1]

    raise RuntimeError(
        "未找到 ffmpeg。请安装 ffmpeg，或设置 FFMPEG_BIN，"
        "或将 ffmpeg 放到项目目录的 ffmpeg-local-*/bin/ffmpeg"
    )


def run_ffmpeg_transcode(
    ffmpeg_bin: str,
    in_path: str,
    out_path: str,
    volume_percent: int,
    mp3_quality: int,
    target_bytes: int,
    requested_sample_rate: int = 0,
    compression_enabled: bool = True,
    reference_22_enabled: bool = False,
):
    volume = max(0.0, volume_percent / 100.0)
    if reference_22_enabled:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            in_path,
            "-vn",
            "-af",
            f"volume={volume:.4f}",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError("高规格模式导出失败。请确认 ffmpeg 支持 libmp3lame 编码器。")
        return

    if not compression_enabled:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            in_path,
            "-vn",
            "-af",
            f"volume={volume:.4f}",
        ]
        if requested_sample_rate:
            cmd.extend(["-ar", str(requested_sample_rate)])
        cmd.extend(["-c:a", "libmp3lame", "-q:a", str(mp3_quality), out_path])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError("mp3 导出失败。请确认 ffmpeg 支持 libmp3lame 编码器。")
        return

    # 去除音频末尾静音：反转后去掉开头静音，再反转回来。
    af_chain = (
        f"volume={volume:.4f},"
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0.20:start_threshold=-45dB,"
        "areverse"
    )
    duration_seconds = probe_duration_seconds(ffmpeg_bin, in_path)
    bitrates = choose_bitrates(mp3_quality, target_bytes, duration_seconds)
    best_tmp = None
    best_size = None

    with tempfile.TemporaryDirectory(prefix="m20_audio_try_") as try_dir:
        for bitrate in bitrates:
            sample_rates = [requested_sample_rate] if requested_sample_rate else choose_sample_rates(bitrate)
            for sample_rate in sample_rates:
                tmp_out = os.path.join(try_dir, f"out_{bitrate}_{sample_rate}.mp3")
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    in_path,
                    "-vn",
                    "-af",
                    af_chain,
                    "-ac",
                    "1",
                    "-ar",
                    str(sample_rate),
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    f"{bitrate}k",
                    tmp_out,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0 or not os.path.exists(tmp_out):
                    cmd_fb = [
                        ffmpeg_bin,
                        "-y",
                        "-i",
                        in_path,
                        "-vn",
                        "-af",
                        af_chain,
                        "-ac",
                        "1",
                        "-ar",
                        str(sample_rate),
                        "-c:a",
                        "mp3",
                        "-b:a",
                        f"{bitrate}k",
                        tmp_out,
                    ]
                    result_fb = subprocess.run(cmd_fb, capture_output=True, text=True)
                    if result_fb.returncode != 0 or not os.path.exists(tmp_out):
                        continue

                out_size = os.path.getsize(tmp_out)
                if best_size is None or out_size < best_size:
                    best_size = out_size
                    best_tmp = tmp_out
                if out_size <= target_bytes:
                    shutil.copyfile(tmp_out, out_path)
                    return

        if best_tmp is not None:
            shutil.copyfile(best_tmp, out_path)
            if requested_sample_rate:
                # 用户明确指定采样率时，优先满足交付规格；前端会提示未达到压缩目标。
                return
            raise RuntimeError(
                f"已降到最接近目标的结果，但最小结果仍为 {best_size} 字节，未达到目标 {target_bytes} 字节。"
            )
        raise RuntimeError("mp3 导出失败。请确认 ffmpeg 支持 mp3 编码器（libmp3lame 或 mp3）。")


class Handler(http.server.SimpleHTTPRequestHandler):
    def cors_origin(self):
        origin = self.headers.get("Origin", "")
        allowed_origins = {PAGES_ORIGIN, "http://127.0.0.1:8000", "http://localhost:8000"}
        return origin if origin in allowed_origins else ""

    def add_cors_headers(self):
        origin = self.cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/transcode":
            self.send_error(404, "Not Found")
            return
        self.send_response(204)
        self.add_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/transcode":
            self.send_error(404, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length <= 0:
            self.send_error(400, "Empty body")
            return
        if length > MAX_UPLOAD_BYTES:
            self.send_response(413, "Payload Too Large")
            self.add_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        try:
            volume_percent = clamp_int(int(params.get("volume_percent", ["100"])[0]), 100, 400)
        except ValueError:
            volume_percent = 100
        try:
            mp3_quality = clamp_int(int(params.get("mp3_quality", ["2"])[0]), 0, 9)
        except ValueError:
            mp3_quality = 2
        compression_enabled = params.get("compression_enabled", ["0"])[0] == "1"
        try:
            target_ratio_percent = clamp_int(int(params.get("target_ratio_percent", ["50"])[0]), 10, 95)
        except ValueError:
            target_ratio_percent = 50
        try:
            requested_sample_rate = int(params.get("sample_rate", ["0"])[0])
        except ValueError:
            requested_sample_rate = 0
        if requested_sample_rate not in (0, 44100):
            requested_sample_rate = 0
        reference_22_enabled = params.get("reference_22_enabled", ["0"])[0] == "1"

        filename = params.get("filename", ["input.m4a"])[0]
        in_ext = os.path.splitext(filename)[1].lower() or ".m4a"

        body = self.rfile.read(length)
        if not body:
            self.send_error(400, "No data")
            return
        target_bytes = max(1, int(len(body) * target_ratio_percent / 100))

        try:
            ffmpeg_bin = resolve_ffmpeg_binary()
        except Exception as exc:
            payload = str(exc).encode("utf-8", errors="replace")
            self.send_response(500)
            self.add_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        with tempfile.TemporaryDirectory(prefix="m20_audio_") as tmpdir:
            in_path = os.path.join(tmpdir, f"input{in_ext}")
            out_path = os.path.join(tmpdir, "output.mp3")
            with open(in_path, "wb") as f:
                f.write(body)

            try:
                run_ffmpeg_transcode(
                    ffmpeg_bin,
                    in_path,
                    out_path,
                    volume_percent,
                    mp3_quality,
                    target_bytes,
                    requested_sample_rate,
                    compression_enabled,
                    reference_22_enabled,
                )
                with open(out_path, "rb") as f:
                    out_data = f.read()
            except Exception as exc:
                payload = str(exc).encode("utf-8", errors="replace")
                self.send_response(500)
                self.add_cors_headers()
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

        self.send_response(200)
        self.add_cors_headers()
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(out_data)))
        self.end_headers()
        self.wfile.write(out_data)


if __name__ == "__main__":
    ffmpeg_bin = resolve_ffmpeg_binary()
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    print(f"Using ffmpeg: {ffmpeg_bin}")
    print("Open http://127.0.0.1:8000 to use backend transcoding.")
    server.serve_forever()
