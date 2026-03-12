import os
import subprocess
import time
import threading
from flask import Flask

app = Flask(__name__)

# ═══════════════════════════════════════════
# الروابط تُقرأ من GitHub Secrets
# ═══════════════════════════════════════════
INPUT_URL  = os.environ.get("INPUT_URL",  "")
OUTPUT_URL = os.environ.get("OUTPUT_URL", "")
# ═══════════════════════════════════════════

stream_status = {"running": False, "retries": 0}

@app.route('/')
def status():
    return f"""
    ✅ Stream Status<br>
    Running: {stream_status['running']}<br>
    Retries: {stream_status['retries']}
    """

def build_ffmpeg_cmd(input_url, output_url):
    return [
        'ffmpeg',
        # ── إعدادات المدخل ──
        '-loglevel', 'warning',
        '-err_detect', 'ignore_err',
        '-fflags', '+genpts+discardcorrupt',
        '-re',
        '-reconnect', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '5',
        '-timeout', '10000000',
        '-i', input_url,

        # ── الفيديو ──
        '-vcodec', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-b:v', '2500k',
        '-maxrate', '2500k',
        '-bufsize', '5000k',
        '-pix_fmt', 'yuv420p',
        '-vf', 'fps=30,scale=1280:-2',
        '-g', '60',
        '-keyint_min', '60',
        '-sc_threshold', '0',

        # ── الصوت ──
        '-acodec', 'aac',
        '-b:a', '96k',
        '-ar', '44100',
        '-ac', '2',
        '-af', 'aresample=async=1000',

        # ── المخرج ──
        '-f', 'flv',
        '-flvflags', 'no_duration_filesize',
        output_url
    ]

def start_stream():
    if not INPUT_URL or not OUTPUT_URL:
        print("❌ ERROR: INPUT_URL or OUTPUT_URL not set in environment/secrets!")
        return

    while True:
        try:
            stream_status['running'] = True
            print(f"🚀 Starting stream... (attempt {stream_status['retries'] + 1})")

            cmd = build_ffmpeg_cmd(INPUT_URL, OUTPUT_URL)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            for line in process.stdout:
                if any(x in line for x in ['Error', 'error', 'fail', 'drop']):
                    print(f"⚠️ {line.strip()}")

            process.wait()

        except Exception as e:
            print(f"❌ Exception: {e}")

        finally:
            stream_status['running'] = False
            stream_status['retries'] += 1
            print(f"🔄 Reconnecting in 3 seconds...")
            time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=start_stream, daemon=True).start()
    app.run(host="0.0.0.0", port=7860)
