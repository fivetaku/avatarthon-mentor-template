#!/usr/bin/env python3
"""아바타톤 멘토 제출물 검사기 (표준 라이브러리만, 아무것도 실행하지 않는다).

검사 항목
  1. 구조: 허용된 폴더·확장자만 있는지, 이중 확장자·심볼릭 링크·실행 권한이 없는지
  2. 파일 정체: 확장자와 실제 내용(매직 바이트)이 맞는지, 실행 파일·압축 파일이 숨어 있지 않은지
  3. 영상: MP4 상자 구조를 끝까지 따라가 파일 뒤에 덧붙인 데이터가 없는지
  4. 크기: 파일당·전체 상한
  5. 개인정보·비밀값: 이메일·전화·주민번호·카드번호·API 키·로블록스 쿠키·내 컴퓨터 경로
  6. SUBMISSION.json 필수 항목

사용: python3 scripts/check_submission.py [레포 경로] [--json]
종료 코드: 0 통과, 1 문제 있음, 2 사용법 오류
"""
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

MB = 1024 * 1024
MAX_FILE = 50 * MB
MAX_VIDEO = 50 * MB
MAX_TOTAL = 120 * MB
MAX_TEXT_SCAN = 5 * MB

# 폴더별 허용 확장자. 키에 없는 최상위 폴더는 거부한다.
TEXT_CODE = {".luau", ".lua", ".json", ".toml", ".md", ".txt", ".yml", ".yaml", ".rbxlx", ".rbxmx", ".csv"}
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED = {
    "game": TEXT_CODE | IMAGES,
    "video": {".mp4"},
    "sessions": {".md"},
    "images": IMAGES,
    "scripts": {".py", ".md"},
    ".claude": {".md"},
    ".github": {".yml", ".yaml"},
}
ROOT_FILES = {"README.md", "PROCESS.md", "SUBMISSION.json", "AGENTS.md", ".gitignore", "LICENSE"}
SKIP_DIRS = {".git"}

# 실행 파일·압축 파일·문서 매크로 등 위험한 정체(매직 바이트)
DANGEROUS_MAGIC = [
    (b"MZ", "Windows 실행 파일(exe/dll)"),
    (b"\x7fELF", "리눅스 실행 파일"),
    (b"\xcf\xfa\xed\xfe", "맥 실행 파일"),
    (b"\xce\xfa\xed\xfe", "맥 실행 파일"),
    (b"\xca\xfe\xba\xbe", "맥 유니버설 실행 파일/자바 클래스"),
    (b"PK\x03\x04", "zip 압축(문서·앱 포함)"),
    (b"Rar!", "rar 압축"),
    (b"7z\xbc\xaf\x27\x1c", "7z 압축"),
    (b"\x1f\x8b", "gzip 압축"),
    (b"\xd0\xcf\x11\xe0", "구형 오피스 문서(매크로 가능)"),
    (b"%PDF", "PDF"),
    (b"{\\rtf", "RTF 문서"),
    (b"\x00asm", "웹어셈블리"),
]
IMAGE_MAGIC = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".webp": [b"RIFF"],
}
BAD_EXT_PARTS = {".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".scr", ".com", ".msi",
                 ".sh", ".app", ".dmg", ".pkg", ".jar", ".zip", ".rar", ".7z", ".iso", ".lnk", ".hta"}

PII_PATTERNS = [
    ("이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("전화번호", re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    ("주민등록번호", re.compile(r"(?<!\d)\d{6}-?[1-4]\d{6}(?!\d)")),
    ("카드번호", re.compile(r"(?<!\d)(?:\d{4}[- ]){3}\d{4}(?!\d)")),
    ("OpenAI/Anthropic 키", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("GitHub 토큰", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("Google API 키", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("AWS 키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack 토큰", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("xAI 키", re.compile(r"\bxai-[A-Za-z0-9]{20,}")),
    ("개인 키", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("로블록스 로그인 쿠키", re.compile(r"_\|WARNING:-DO-NOT-SHARE-THIS|\.ROBLOSECURITY", re.I)),
    ("Bearer 토큰", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}")),
    ("내 컴퓨터 사용자 경로", re.compile(r"/Users/(?!\[)[^/\s]+/|/home/(?!\[)[^/\s]+/|[A-Za-z]:\\Users\\(?!\[)[^\\\s]+\\")),
]
# 예시 문서에 일부러 넣은 값은 허용
PII_ALLOW = {"gptaku@axwith.com", "noreply@github.com", "example@example.com"}


def git_files(root):
    """git 레포면 커밋될 파일(추적 + .gitignore 밖 새 파일)만 본다. 아니면 None."""
    if not (root / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "-co", "--exclude-standard", "-z"],
                             cwd=root, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [root / x for x in out.stdout.decode("utf-8", "replace").split("\0") if x and ((root / x).exists() or (root / x).is_symlink())]


def rel(p, root):
    return p.relative_to(root).as_posix()


def head(path, n=16):
    with open(path, "rb") as f:
        return f.read(n)


def mp4_problems(path):
    """MP4 최상위 상자를 끝까지 따라간다. 상자 합계가 파일 크기와 다르면 뒤에 무언가 붙은 것."""
    size = path.stat().st_size
    probs = []
    with open(path, "rb") as f:
        first = f.read(12)
        if len(first) < 12 or first[4:8] != b"ftyp":
            return ["MP4 시작 상자(ftyp)가 없다 — mp4가 아닌 파일"]
        f.seek(0)
        pos = 0
        seen = set()
        known = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"uuid", b"meta", b"moof", b"mfra",
                 b"sidx", b"styp", b"pdin", b"udta", b"emsg", b"prft"}
        while pos < size:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                probs.append(f"{pos}바이트 지점에 상자 조각이 남아 있다(덧붙인 데이터 의심)")
                break
            box_size = int.from_bytes(hdr[:4], "big")
            box_type = hdr[4:8]
            if box_size == 1:
                ext = f.read(8)
                box_size = int.from_bytes(ext, "big")
            elif box_size == 0:
                box_size = size - pos
            if box_size < 8 or pos + box_size > size:
                probs.append(f"{pos}바이트 지점 상자 크기가 맞지 않는다(손상 또는 덧붙인 데이터)")
                break
            if box_type not in known:
                probs.append(f"알 수 없는 최상위 상자 {box_type!r} — 덧붙인 데이터 의심")
                break
            seen.add(box_type)
            pos += box_size
        if b"moov" not in seen and b"moof" not in seen:
            probs.append("영상 정보 상자(moov)가 없다")
    return probs


def scan_text(path):
    hits = []
    if path.stat().st_size > MAX_TEXT_SCAN:
        return [("크기", "글 파일이 5MB를 넘어 검사하지 못했다")]
    text = path.read_text(encoding="utf-8", errors="replace")
    for name, pat in PII_PATTERNS:
        for m in pat.finditer(text):
            val = m.group(0)
            if val in PII_ALLOW:
                continue
            line = text.count("\n", 0, m.start()) + 1
            masked = val[:3] + "…" if len(val) > 4 else "…"
            hits.append((name, f"{line}행 ({masked})"))
    return hits


def check(root):
    root = Path(root).resolve()
    problems, warnings = [], []
    total = 0
    files = git_files(root)
    for dirpath, dirnames, filenames in ([] if files is not None else os.walk(root, followlinks=False)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for d in list(dirnames):
            dp = Path(dirpath) / d
            if dp.is_symlink():
                problems.append(f"{rel(dp, root)}: 심볼릭 링크 폴더는 받지 않는다")
                dirnames.remove(d)
        for fn in filenames:
            files.append(Path(dirpath) / fn)
    files = files or []

    for p in sorted(files):
        r = rel(p, root)
        if p.is_symlink():
            problems.append(f"{r}: 심볼릭 링크는 받지 않는다")
            continue
        st = p.stat()
        total += st.st_size
        parts = r.split("/")
        top = parts[0]
        ext = p.suffix.lower()
        name_lower = p.name.lower()

        # 1. 구조
        if len(parts) == 1:
            if p.name not in ROOT_FILES:
                problems.append(f"{r}: 최상위에는 README·PROCESS·SUBMISSION.json만 둔다")
                continue
        elif top not in ALLOWED:
            problems.append(f"{r}: 허용되지 않은 폴더 '{top}'")
            continue
        elif ext not in ALLOWED[top]:
            problems.append(f"{r}: '{top}' 폴더에 '{ext or '확장자 없음'}' 파일은 받지 않는다")
            continue
        inner = [("." + s) for s in name_lower.split(".")[1:-1]]
        if any(x in BAD_EXT_PARTS for x in inner):
            problems.append(f"{r}: 이중 확장자(실행 파일 위장 의심)")
            continue
        if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) and top != "scripts":
            problems.append(f"{r}: 실행 권한이 켜져 있다")

        # 4. 크기
        limit = MAX_VIDEO if top == "video" else MAX_FILE
        if st.st_size > limit:
            problems.append(f"{r}: {st.st_size // MB}MB — 상한 {limit // MB}MB 초과")
            continue
        if st.st_size == 0:
            warnings.append(f"{r}: 빈 파일")
            continue

        # 2. 파일 정체
        h = head(p)
        bad = next((label for magic, label in DANGEROUS_MAGIC if h.startswith(magic)), None)
        if bad and not (ext == ".webp" and h.startswith(b"RIFF")):
            problems.append(f"{r}: 확장자는 {ext}인데 실제 내용은 {bad}")
            continue
        if ext in IMAGE_MAGIC:
            if not any(h.startswith(m) for m in IMAGE_MAGIC[ext]) or (ext == ".webp" and h[8:12] != b"WEBP"):
                problems.append(f"{r}: 이미지 확장자인데 실제 이미지가 아니다")
            continue

        # 3. 영상
        if ext == ".mp4":
            for msg in mp4_problems(p):
                problems.append(f"{r}: {msg}")
            continue

        # 5. 글 파일 개인정보·비밀값
        if b"\x00" in h:
            problems.append(f"{r}: 글 파일이어야 하는데 바이너리다")
            continue
        if h.startswith(b"#!") and top != "scripts":
            problems.append(f"{r}: 실행 스크립트(#!)는 scripts 폴더 밖에 둘 수 없다")
        if top in {"scripts", ".github", ".claude"} or p.name in {"README.md", "AGENTS.md"}:
            continue  # 템플릿이 준 파일은 예시 패턴을 담고 있어 건너뛴다
        for kind, where in scan_text(p):
            problems.append(f"{r}: {kind} 발견 — {where}")

    if total > MAX_TOTAL:
        problems.append(f"전체 {total // MB}MB — 상한 {MAX_TOTAL // MB}MB 초과")

    # 6. 필수 제출물
    sub = root / "SUBMISSION.json"
    if not sub.is_file():
        problems.append("SUBMISSION.json이 없다")
    else:
        try:
            meta = json.loads(sub.read_text(encoding="utf-8"))
            for key in ("nickname", "coding_ai", "roblox_game_url", "one_line"):
                if not str(meta.get(key, "")).strip():
                    problems.append(f"SUBMISSION.json: '{key}' 칸이 비었다")
            url = str(meta.get("roblox_game_url", ""))
            if url and not re.match(r"^https://(www\.)?roblox\.com/(games|share)", url):
                problems.append("SUBMISSION.json: roblox_game_url은 roblox.com 게임 주소여야 한다")
        except json.JSONDecodeError as e:
            problems.append(f"SUBMISSION.json 형식 오류: {e}")
    def has(folder, pattern):
        d = root / folder
        return d.is_dir() and any(x.is_file() for x in d.rglob(pattern))

    if not has("video", "*.mp4"):
        problems.append("video 폴더에 플레이 영상(mp4)이 없다")
    if not has("sessions", "*.md"):
        problems.append("sessions 폴더에 AI 대화 기록이 없다")
    if not has("game", "*"):
        problems.append("game 폴더에 게임 소스가 없다")
    proc = root / "PROCESS.md"
    ptext = proc.read_text(encoding="utf-8", errors="replace") if proc.is_file() else ""
    if len(ptext.strip()) < 200:
        problems.append("PROCESS.md(과정 정리)가 없거나 너무 짧다")
    elif "(여기에" in ptext:
        problems.append("PROCESS.md에 아직 채우지 않은 '(여기에 …)' 칸이 있다")

    return {"root": str(root), "files": len(files), "total_mb": round(total / MB, 1),
            "problems": problems, "warnings": warnings, "passed": not problems}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    root = args[0] if args else "."
    if not Path(root).is_dir():
        print(f"폴더가 없다: {root}", file=sys.stderr)
        return 2
    res = check(root)
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"검사 대상: {res['root']} (파일 {res['files']}개, {res['total_mb']}MB)")
        for w in res["warnings"]:
            print(f"  주의: {w}")
        for pr in res["problems"]:
            print(f"  문제: {pr}")
        print("통과" if res["passed"] else f"문제 {len(res['problems'])}건 — 고친 뒤 다시 검사하세요")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
