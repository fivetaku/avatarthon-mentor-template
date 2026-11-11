#!/usr/bin/env python3
"""플레이 영상을 제출용 mp4로 다시 만든다(ffmpeg 필요).

- 새 mp4로 다시 인코딩하므로 원본 뒤에 붙은 데이터·위치 정보 같은 메타데이터가 남지 않는다.
- 720p, 최대 3분 30초, 45MB 이하가 될 때까지 화질을 낮춰 다시 만든다.

사용: python3 scripts/prepare_video.py <원본 영상> [--out video/play.mp4]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LIMIT = 45 * 1024 * 1024

for _stream in (sys.stdout, sys.stderr):   # 윈도우 콘솔(cp949)에서 멈추지 않게
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="video/play.mp4")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg가 없습니다. 맥은 'brew install ffmpeg', 윈도우는 'winget install ffmpeg'로 설치한 뒤 다시 실행하세요.")
    src = Path(a.src).expanduser()
    if not src.is_file():
        sys.exit(f"영상 파일이 없습니다: {src}")
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                                   capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        dur = 0
    if dur > 210:
        print(f"영상이 {int(dur // 60)}분 {int(dur % 60)}초입니다. 앞 3분 30초만 남깁니다. "
              "보여 주고 싶은 장면이 뒤에 있으면 먼저 잘라서 다시 실행하세요.")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.mp4")
    for crf in (26, 30, 34, 38):
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", "210",
               "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "-1", "-map_chapters", "-1",
               "-vf", "scale=-2:'min(720,ih)'", "-r", "30",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(tmp)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            tmp.unlink(missing_ok=True)
            sys.exit(f"영상 변환 실패: {r.stderr.strip()[-400:]}")
        size = tmp.stat().st_size
        if size <= LIMIT:
            tmp.replace(out)
            print(f"저장: {out} ({size / 1024 / 1024:.1f}MB, 화질 crf {crf})")
            return
    tmp.unlink(missing_ok=True)
    sys.exit("45MB 아래로 줄이지 못했습니다. 영상을 3분 안으로 잘라 다시 시도하세요.")


if __name__ == "__main__":
    main()
