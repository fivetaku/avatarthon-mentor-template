#!/usr/bin/env python3
"""아바타톤 멘토 제출물 검사기 (표준 라이브러리만, 아무것도 실행하지 않는다).

검사 항목
  1. 구조: 허용된 폴더·확장자만 있는지, 이중 확장자·보이지 않는 글자·심볼릭 링크·실행 권한이 없는지
  2. 파일 정체: 확장자와 실제 내용(매직 바이트)이 맞는지, 이미지 끝에 다른 파일이 붙어 있지 않은지
     3D 파일(.glb·.fbx)도 머리 부분과 크기 정보를 확인한다
  3. 영상: video/play.mp4 하나만, MP4 상자 구조를 끝까지 따라가 덧붙인 데이터·큰 부가 상자가 없는지
  4. 크기: 파일당·전체 상한
  5. 개인정보·비밀값: 이메일·전화·주민번호·카드·계좌·주소·API 키·토큰·로블록스 쿠키·내 컴퓨터 경로
  6. 필수 제출물: game/·assets/(둘 다 비어 있지 않게), video/play.mp4, sessions/, PROCESS.md,
     SUBMISSION.json(tool은 "VARCO"·"Blender"·"기타" 중 하나)

개인정보 규칙(RULES)은 scripts/export_sessions.py도 그대로 가져다 쓴다(지우는 규칙과 찾는 규칙이 같다).

사용: python3 scripts/check_submission.py [레포 경로] [--json]
종료 코드: 0 통과, 1 문제 있음, 2 사용법 오류
"""
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path

MB = 1024 * 1024
MAX_FILE = 50 * MB
MAX_VIDEO = 50 * MB
MAX_TOTAL = 120 * MB
MAX_SIDE_BOXES = 256 * 1024  # mp4의 free·uuid·udta 같은 부가 상자 합계 상한

TEXT_CODE = {".luau", ".lua", ".json", ".toml", ".md", ".txt", ".yml", ".yaml", ".rbxlx", ".rbxmx", ".csv"}
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
# 에셋: 이미지(텍스처·원화), 3D 모델, 로블록스 모델(XML), 설명 글.
# .blend(Blender 원본)와 .rbxm(로블록스 바이너리 모델)은 받지 않는다 — 안을 글로 읽어 검사할 수 없고,
# .blend는 파일 안에 파이썬 스크립트를 넣을 수 있어서다. FBX·OBJ·GLB와 .rbxmx로 내보내 넣는다.
MODELS_TEXT = {".obj", ".mtl", ".gltf", ".rbxmx"}
MODELS_BIN = {".fbx", ".glb"}   # .fbx는 글(ASCII) 형식이면 글로 검사한다
ASSET_EXTS = IMAGES | MODELS_TEXT | MODELS_BIN | {".md", ".txt"}
ASSET_REQUIRED = IMAGES | MODELS_TEXT | MODELS_BIN   # assets/에 적어도 하나는 있어야 하는 실제 에셋
GAME_REQUIRED = {".rbxlx", ".rbxmx", ".luau", ".lua", ".json", ".toml"}   # game/에 적어도 하나는 있어야 하는 게임 파일
TOOLS = ("VARCO", "Blender", "기타")   # 구글 폼 선택지와 같은 문자열
ALLOWED = {
    "game": TEXT_CODE | IMAGES,
    "assets": ASSET_EXTS,
    "video": {".mp4"},
    "sessions": {".md"} | IMAGES,
    "images": IMAGES,
    "scripts": {".py", ".md"},
    "docs": {".md"},
    ".claude": {".md"},
    ".github": {".yml", ".yaml"},
}
ROOT_FILES = {"README.md", "PROCESS.md", "SUBMISSION.json", "AGENTS.md", ".gitignore", "LICENSE"}
TEMPLATE_DIRS = {"scripts", ".github", ".claude", "docs"}  # 템플릿이 준 폴더. 내용은 운영진 쪽에서 원본과 바이트 비교한다

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
# 영상 부가 상자·이미지 안에서 찾는 다른 파일의 흔적
PAYLOAD_SIGS = [(b"PK\x03\x04", "zip 압축"), (b"PK\x05\x06", "zip 압축"), (b"\x7fELF", "리눅스 실행 파일"),
                (b"\xcf\xfa\xed\xfe", "맥 실행 파일"), (b"Rar!\x1a", "rar 압축"), (b"7z\xbc\xaf\x27\x1c", "7z 압축"),
                (b"This program cannot be run in DOS mode", "Windows 실행 파일"), (b"PE\x00\x00", "Windows 실행 파일")]
BAD_EXT_PARTS = {".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".scr", ".com", ".msi",
                 ".sh", ".app", ".dmg", ".pkg", ".jar", ".zip", ".rar", ".7z", ".iso", ".lnk", ".hta"}

# ── 개인정보·비밀값 규칙 ─────────────────────────────────────────────
# (이름, 정규식, 바꿀 꼬리표, 옵션). 옵션: "scrub" = 지우기만 하고 검사에선 안 봄,
# "text" = game/ 폴더 파일에선 검사하지 않음(좌표·ID 숫자 오탐 방지).
# 모든 값 부분에 (?!\[)를 둬서 이미 지운 꼬리표([삭제] 등)는 다시 잡지 않는다.
S = r"[\s.\-–—_]*"   # 숫자 사이 구분자(공백·점·하이픈·en dash·밑줄)
BANKS = (r"카카오뱅크|카뱅|신한|국민|KB|우리|하나|농협|NH|기업|IBK|토스뱅크|토스|케이뱅크|새마을|우체국|SC제일|씨티|수협|"
         r"부산은행|대구은행|경남은행|광주은행|전북은행|제주은행|계좌번호|계좌|예금주")
RULES = [
    ("개인 키", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----)?", re.S), "[개인키 삭제]", ""),
    ("로블록스 로그인 쿠키", re.compile(r"_\|WARNING:-DO-NOT-SHARE-THIS[^\s\"']*"), "[로블록스 쿠키 삭제]", ""),
    ("로블록스 로그인 쿠키", re.compile(r"(?i)(\.?ROBLOSECURITY[\"']?\s*[:=]\s*[\"']?)(?!\[)[^\s\"';]{16,}"), r"\1[삭제]", ""),
    ("API 키", re.compile(r"\bsk-(?:ant-|proj-|or-)?(?!\[)[A-Za-z0-9_-]{20,}"), "[키 삭제]", ""),
    ("API 키", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}"), "[키 삭제]", ""),
    ("GitHub·GitLab 토큰", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}|\bglpat-[A-Za-z0-9_-]{20,}"), "[키 삭제]", ""),
    ("API 키", re.compile(r"\b(?:hf|gsk|r8)_[A-Za-z0-9]{20,}"), "[키 삭제]", ""),
    ("Google API 키", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "[키 삭제]", ""),
    ("AWS 키", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[키 삭제]", ""),
    ("Slack 토큰", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[키 삭제]", ""),
    ("xAI 키", re.compile(r"\bxai-[A-Za-z0-9]{20,}"), "[키 삭제]", ""),
    ("Discord 토큰", re.compile(r"\b[MNO][A-Za-z0-9_-]{23,27}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,40}"), "[키 삭제]", ""),
    ("Discord 웹훅", re.compile(r"(discord(?:app)?\.com/api/webhooks/)(?!\[)\d+/[A-Za-z0-9_-]+"), r"\1[삭제]", ""),
    ("JWT 토큰", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[키 삭제]", ""),
    ("텔레그램 봇 토큰", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}"), "[키 삭제]", ""),
    ("인증 헤더", re.compile(r"\b(Bearer|Basic)\s+(?!\[)[A-Za-z0-9._~+/=-]{12,}"), r"\1 [키 삭제]", ""),
    ("주소 속 비밀번호", re.compile(r"(https?://)(?!\[)[^/\s:@\"']+:[^/\s@\"']+@"), r"\1[삭제]@", ""),
    ("비밀값", re.compile(r"(?i)(?<![A-Za-z0-9])((?:[A-Za-z0-9]+[_-])*(?:api[_-]?key|apikey|access[_-]?key|token|secret|password|passwd|pwd|"
                         r"cookie|open[_-]?cloud|credentials?)s?[\"']?\s*[:=]\s*[\"']?)(?!\[)[^\s\"',;]{8,}"), r"\1[삭제]", "text"),
    ("비밀값", re.compile(r"(?i)(?<![A-Za-z0-9_])((?:[A-Za-z0-9]+_)+key[\"']?\s*[:=]\s*[\"']?)(?!\[)[^\s\"',;]{16,}"), r"\1[삭제]", "text"),
    ("비밀값", re.compile(r"(?i)(--?(?:api[_-]?key|token|secret|password|cookie)[\s=]+[\"']?)(?!\[)[^\s\"']{8,}"), r"\1[삭제]", ""),
    ("비밀번호", re.compile(r"((?:비밀번호|패스워드|비번)\s*(?:[:=]|은|는)\s*[\"']?)(?![\[\s])[^\s\"',.ㄱ-힣]{4,}"), r"\1[삭제]", "text"),
    ("이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[이메일]", ""),
    ("내 컴퓨터 사용자 경로", re.compile(r"(?i)\b([A-Z]:(?:\\\\|\\|/)+users(?:\\\\|\\|/)+)(?!\[)[^\\/\r\n\"'<>|:*?\sㄱ-힣]"
                                  r"(?:[^\\/\r\n\"'<>|:*?ㄱ-힣]*[^\\/\r\n\"'<>|:*?\sㄱ-힣])?"), r"\1[사용자]", ""),
    ("내 컴퓨터 사용자 경로", re.compile(r"(/(?:Users|home)/)(?!\[)(?!Shared\b)[^/\s\"'`:;,)\]]+"), r"\1[사용자]", ""),
    ("내 컴퓨터 사용자 경로", re.compile(r"(?i)(\\\\wsl[^\\\s]*\\[^\\\s]+\\home\\)(?!\[)[^\\\s\"']+"), r"\1[사용자]", ""),
    ("주민·외국인등록번호", re.compile(r"(?<![\d.])\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[\s\-–]*[1-8]\d{6}(?!\d)"), "[주민번호]", "text"),
    ("카드번호", re.compile(r"(?<![\d.])(?:\d{4}[\s\-–]){3}\d{4}(?!\d)|(?<![\d.])\d{4}[\s\-–]\d{6}[\s\-–]\d{5}(?!\d)|(?<![\d.])\d{16}(?!\d)"), "[카드번호]", "text"),
    ("전화번호", re.compile(r"(?<![\d.])(?:\+?82" + S + r"\(?0?\)?" + S + r"|\(?0)1[016789]\)?" + S + r"\d{3,4}" + S + r"\d{4}(?!\d)"), "[전화번호]", "text"),
    ("전화번호", re.compile(r"(?<![\d.])\(?0(?:2|[3-6][1-5]|70)\)?[\s.\-–]+\d{3,4}[\s.\-–]+\d{4}(?!\d)"), "[전화번호]", "text"),
    ("계좌번호", re.compile(r"((?:" + BANKS + r")[^\d\n\[]{0,12})\d{2,6}(?:[\s\-–]\d{2,7}){1,3}(?!\d)"), r"\1[계좌번호]", "text"),
    ("주소", re.compile(r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)\S*\s+"
                       r"(?:\S+(?:시|군|구)\s+){1,2}(?:\S+\s+)?\S+(?:로|길)\s*\d+(?:-\d+)?(?:[,\s]+\S*동\s*\d+호|[,\s]+\d+호)?"), "[주소]", "text"),
    ("IP 주소", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), "[IP]", "scrub"),
]
# 예시 문서에 일부러 넣은 값은 허용
PII_ALLOW = {"gptaku@axwith.com", "noreply@github.com", "noreply@anthropic.com", "example@example.com"}


def normalize(text):
    """전각 숫자·전각 @·NBSP 같은 변형을 보통 글자로 맞춘다(NFKC)."""
    return unicodedata.normalize("NFKC", text)


def scrub(text, in_game=False):
    """개인정보·비밀값을 꼬리표로 바꾼다(export_sessions·organize가 쓴다).

    in_game=True면 게임·3D 파일용: 키·쿠키·이메일·내 컴퓨터 경로만 지우고, 숫자형 규칙(전화·카드·IP 등)은
    좌표·ID를 망가뜨리지 않게 건너뛴다.
    """
    text = normalize(text)
    for _name, pat, rep, opt in RULES:
        if in_game and opt in ("text", "scrub"):
            continue
        text = pat.sub(lambda m, rep=rep: m.group(0) if m.group(0) in PII_ALLOW else m.expand(rep), text)
    return text


def find_pii(text, in_game=False):
    hits = []
    text = normalize(text)
    for name, pat, _rep, opt in RULES:
        if opt == "scrub" or (in_game and opt == "text"):
            continue
        for m in pat.finditer(text):
            val = m.group(0)
            if val in PII_ALLOW:
                continue
            line = text.count("\n", 0, m.start()) + 1
            masked = val[:3] + "…" if len(val) > 4 else "…"
            hits.append((name, f"{line}행 ({masked})"))
    return hits


def decode_text(raw):
    """BOM을 보고 글로 바꾼다. UTF-16이면 None(다시 저장 안내)."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return None
    return raw.decode("utf-8-sig", errors="replace")


def read_text_file(path):
    return decode_text(Path(path).read_bytes())


# ── 파일 목록 ─────────────────────────────────────────────────────
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
    names = [x for x in out.stdout.decode("utf-8", "replace").split("\0") if x]
    return [root / x for x in names if (root / x).exists() or (root / x).is_symlink()]


def walk_files(root, problems):
    files = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for d in list(dirnames):
            dp = Path(dirpath) / d
            if dp.is_symlink():
                problems.append(f"{rel(dp, root)}: 심볼릭 링크 폴더는 받지 않는다")
                dirnames.remove(d)
        files += [Path(dirpath) / fn for fn in filenames]
    return files


def rel(p, root):
    return p.relative_to(root).as_posix()


def bad_name(name):
    """보이지 않는 서식 글자(오른쪽→왼쪽 표시 등)나 점처럼 보이는 글자로 확장자를 속이는 이름."""
    return any(unicodedata.category(c) in ("Cf", "Cc", "Co", "Cs") for c in name) or any(
        c in name for c in "․‧．。⸮﹒")


# ── 정체 검사 ─────────────────────────────────────────────────────
def mp4_problems(path):
    """MP4 최상위 상자를 끝까지 따라간다. 상자 합계가 파일 크기와 다르거나 부가 상자가 크면 문제."""
    size = path.stat().st_size
    probs = []
    known = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"uuid", b"meta", b"moof", b"mfra",
             b"sidx", b"styp", b"pdin", b"udta", b"emsg", b"prft"}
    core = {b"ftyp", b"moov", b"mdat", b"moof", b"mfra", b"sidx", b"styp"}
    side = 0
    seen = set()
    with open(path, "rb") as f:
        first = f.read(12)
        if len(first) < 12 or first[4:8] != b"ftyp":
            return ["MP4 시작 상자(ftyp)가 없다 — mp4가 아닌 파일"]
        pos = 0
        while pos < size:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                probs.append(f"{pos}바이트 지점에 상자 조각이 남아 있다(덧붙인 데이터 의심)")
                break
            box_size = int.from_bytes(hdr[:4], "big")
            box_type = hdr[4:8]
            if box_size == 1:
                box_size = int.from_bytes(f.read(8), "big")
            elif box_size == 0:
                box_size = size - pos
            if box_size < 8 or pos + box_size > size:
                probs.append(f"{pos}바이트 지점 상자 크기가 맞지 않는다(손상 또는 덧붙인 데이터)")
                break
            if box_type not in known:
                probs.append(f"알 수 없는 최상위 상자 {box_type!r} — 덧붙인 데이터 의심")
                break
            if box_type not in core:
                if hdr[:4] == b"\x00\x00\x00\x00" and pos + box_size == size and box_size > 8:
                    probs.append(f"파일 끝까지 이어지는 부가 상자 {box_type!r} — 덧붙인 데이터 의심")
                    break
                side += box_size
                f.seek(pos + 8)
                body = f.read(min(box_size, MAX_SIDE_BOXES + 1))
                hit = next((label for magic, label in PAYLOAD_SIGS if magic in body), None)
                if hit:
                    probs.append(f"부가 상자 {box_type!r} 안에 숨은 {hit} 흔적이 있다")
                    break
            seen.add(box_type)
            pos += box_size
    if side > MAX_SIDE_BOXES:
        probs.append(f"영상이 아닌 부가 상자가 {side // 1024}KB — 다른 파일을 숨긴 것으로 의심(prepare_video.py로 다시 만드세요)")
    if b"moov" not in seen and b"moof" not in seen:
        probs.append("영상 정보 상자(moov)가 없다")
    return probs


def image_problems(path, ext):
    data = path.read_bytes()
    if ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "이미지 확장자인데 실제 PNG가 아니다"
        if not data.endswith(b"IEND\xaeB`\x82"):
            return "PNG 끝(IEND) 뒤에 다른 데이터가 붙어 있다"
    elif ext in (".jpg", ".jpeg"):
        if not data.startswith(b"\xff\xd8\xff"):
            return "이미지 확장자인데 실제 JPEG가 아니다"
        if not data.rstrip(b"\x00").endswith(b"\xff\xd9"):
            return "JPEG 끝(EOI) 뒤에 다른 데이터가 붙어 있다"
    elif ext == ".webp":
        if not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
            return "이미지 확장자인데 실제 WebP가 아니다"
        if int.from_bytes(data[4:8], "little") + 8 != len(data):
            return "WebP 크기 정보와 파일 크기가 다르다(덧붙인 데이터 의심)"
    for magic, label in PAYLOAD_SIGS[:6]:
        if magic in data:
            return f"이미지 안에 {label} 데이터가 들어 있다"
    return None


def image_has_metadata(path, ext):
    """사진 정보(EXIF — 찍은 위치가 들어갈 수 있다)가 남아 있는지 본다."""
    data = path.read_bytes()[:256 * 1024]
    if ext in (".jpg", ".jpeg"):
        return b"Exif\x00\x00" in data
    if ext == ".png":
        return b"eXIf" in data
    if ext == ".webp":
        return b"EXIF" in data[:4096]
    return False


def model_problems(path, ext):
    """바이너리 3D 파일을 본다. 돌려주는 값: (문제, 주의). 글(ASCII) FBX면 (None, None) — 글 검사로 넘긴다.

    GLB는 조각(chunk) 크기를 끝까지 따라가 덧붙인 데이터를 잡는다. 압축된 텍스처가 든 바이너리는
    우연히 zip 머리와 같은 4바이트가 나올 수 있어서, 숨은 파일 흔적은 문제가 아니라 주의로 알린다.
    """
    data = path.read_bytes()
    if ext == ".glb":
        if not data.startswith(b"glTF"):
            return "확장자는 .glb인데 실제 glTF 바이너리가 아니다", None
        if int.from_bytes(data[8:12], "little") != len(data):
            return "GLB 크기 정보와 파일 크기가 다르다(덧붙인 데이터 의심)", None
        pos = 12
        while pos < len(data):
            if pos + 8 > len(data):
                return "GLB 끝에 조각이 남아 있다(덧붙인 데이터 의심)", None
            n = int.from_bytes(data[pos:pos + 4], "little")
            if pos + 8 + n > len(data):
                return "GLB 조각 크기가 맞지 않는다(손상 또는 덧붙인 데이터)", None
            pos += 8 + n
    elif ext == ".fbx":
        if not data.startswith(b"Kaydara FBX Binary"):
            if b"\x00" in data[:4096]:
                return "확장자는 .fbx인데 실제 FBX 파일이 아니다", None
            return None, None
    hit = next((label for magic, label in PAYLOAD_SIGS if magic in data), None)
    return "", (f"3D 파일 안에 {hit} 머리와 같은 바이트가 있다 — 운영진이 확인한다" if hit else None)


# ── 검사 ─────────────────────────────────────────────────────────
def check(root):
    root = Path(root).resolve()
    problems, warnings = [], []
    total = 0
    files = git_files(root)
    if files is None:
        files = walk_files(root, problems)

    for p in sorted(files):
        r = rel(p, root)
        if p.is_symlink():
            problems.append(f"{r}: 심볼릭 링크는 받지 않는다")
            continue
        if p.is_dir():
            problems.append(f"{r}: 폴더 안에 .git이 있어 내용 없이 링크로만 올라간다 — .git을 빼고 다시 복사하세요")
            continue
        st = p.stat()
        total += st.st_size
        parts = r.split("/")
        top = parts[0]
        ext = p.suffix.lower()

        # 1. 구조
        if any(bad_name(x) for x in parts):
            problems.append(f"{r}: 이름에 보이지 않는 글자나 점처럼 보이는 글자가 있다(확장자 위장 의심)")
            continue
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
        if top == "video" and r != "video/play.mp4":
            problems.append(f"{r}: video 폴더에는 prepare_video.py가 만든 play.mp4 하나만 둔다(원본 영상은 위치 정보가 남을 수 있다)")
            continue
        inner = [("." + s) for s in normalize(p.name).lower().split(".")[1:-1]]
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
        with open(p, "rb") as f:
            h = f.read(16)
        bad = next((label for magic, label in DANGEROUS_MAGIC if h.startswith(magic)), None)
        if bad:
            problems.append(f"{r}: 확장자는 {ext}인데 실제 내용은 {bad}")
            continue
        if ext in IMAGES:
            msg = image_problems(p, ext)
            if msg:
                problems.append(f"{r}: {msg}")
            elif image_has_metadata(p, ext):
                warnings.append(f"{r}: 사진 정보(EXIF, 찍은 위치가 들어갈 수 있다)가 남아 있다 — scripts/organize.py로 복사하면 지워진다")
            if top == "sessions":
                warnings.append(f"{r}: 스크린샷 속 이름·이메일·얼굴은 자동으로 못 찾는다 — 직접 확인하세요")
            continue
        if ext in MODELS_BIN:
            msg, note = model_problems(p, ext)
            if msg:
                problems.append(f"{r}: {msg}")
            if note:
                warnings.append(f"{r}: {note}")
            if msg is not None:
                continue   # 바이너리 3D 파일은 글 검사를 하지 않는다

        # 3. 영상
        if ext == ".mp4":
            for msg in mp4_problems(p):
                problems.append(f"{r}: {msg}")
            continue

        # 5. 글 파일
        raw = p.read_bytes()
        text = decode_text(raw)
        if text is None:
            problems.append(f"{r}: UTF-16으로 저장된 글이다 — UTF-8로 다시 저장하세요")
            continue
        if "\x00" in text:
            problems.append(f"{r}: 글 파일이어야 하는데 바이너리 데이터가 섞여 있다")
            continue
        if text.startswith("#!") and top != "scripts":
            problems.append(f"{r}: 실행 스크립트(#!)는 scripts 폴더 밖에 둘 수 없다")
        if ext == ".md" and re.search(r"(?i)<\s*(?:script|iframe|object|embed)\b|javascript:", text):
            problems.append(f"{r}: 글 안에 스크립트·iframe 같은 실행 요소가 있다")
        if top in TEMPLATE_DIRS and len(parts) > 1:
            continue  # 템플릿 파일은 예시 패턴을 담고 있다. 바뀌었는지는 운영진 쪽에서 원본과 비교한다
        # 게임·3D 파일은 좌표·ID 숫자가 많아 숫자형 개인정보(전화·카드 등)는 보지 않는다. 설명 글(.md·.txt)은 다 본다
        numeric_ok = top == "game" or (top == "assets" and ext not in (".md", ".txt"))
        for kind, where in find_pii(text, in_game=numeric_ok):
            problems.append(f"{r}: {kind} 발견 — {where}")

    if total > MAX_TOTAL:
        problems.append(f"전체 {total // MB}MB — 상한 {MAX_TOTAL // MB}MB 초과")

    # 6. 필수 제출물
    sub = root / "SUBMISSION.json"
    if not sub.is_file():
        problems.append("SUBMISSION.json이 없다")
    else:
        try:
            meta = json.loads(read_text_file(sub) or "")
            if not isinstance(meta, dict):
                meta = {}
                problems.append("SUBMISSION.json은 { … } 형태여야 한다(템플릿 칸을 채워 주세요)")
            for key in ("nickname", "tool", "roblox_game_url", "one_line"):
                if not str(meta.get(key, "")).strip():
                    problems.append(f"SUBMISSION.json: '{key}' 칸이 비었다")
            tool = meta.get("tool", "")
            tool = unicodedata.normalize("NFC", tool) if isinstance(tool, str) else tool
            if tool and tool not in TOOLS:
                problems.append(f"SUBMISSION.json: tool은 {' · '.join(chr(34) + t + chr(34) for t in TOOLS)} 중 하나를 그대로 써야 한다"
                                f"(지금 값: {str(tool)[:20]!r})")
            if tool == "기타" and not str(meta.get("tool_other", "")).strip():
                warnings.append("SUBMISSION.json: tool이 '기타'면 tool_other에 쓴 도구 이름을 적어 주세요")
            url = str(meta.get("roblox_game_url", ""))
            if url and not re.match(r"^https://(?:(?:www\.)?roblox\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:games|share)"
                                    r"|create\.roblox\.com/dashboard/creations/experiences/\d+)", url):
                problems.append("SUBMISSION.json: roblox_game_url은 roblox.com 게임 주소여야 한다")
        except json.JSONDecodeError as e:
            problems.append(f"SUBMISSION.json 형식 오류(UTF-8로 저장했는지 확인): {e}")

    def has(folder, pattern):
        d = root / folder
        return d.is_dir() and any(x.is_file() for x in d.rglob(pattern))

    if not (root / "video" / "play.mp4").is_file():
        problems.append("video/play.mp4(플레이 영상)가 없다 — scripts/prepare_video.py로 만드세요")
    if not has("sessions", "*"):
        problems.append("sessions 폴더에 작업 기록(대화 기록·메모·스크린샷)이 없다")
    gd = root / "game"
    if not (gd.is_dir() and any(x.is_file() and x.suffix.lower() in GAME_REQUIRED for x in gd.rglob("*"))):
        problems.append("game 폴더가 없거나 비었다 — 게임 파일(.rbxlx 또는 소스)을 넣으세요")
    ad = root / "assets"
    if not (ad.is_dir() and any(x.is_file() and x.suffix.lower() in ASSET_REQUIRED for x in ad.rglob("*"))):
        problems.append("assets 폴더가 없거나 에셋 파일(이미지·.fbx·.obj·.glb·.gltf·.rbxmx)이 없다 — game/과 assets/ 둘 다 있어야 한다")
    proc = root / "PROCESS.md"
    ptext = (read_text_file(proc) or "") if proc.is_file() else ""
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
