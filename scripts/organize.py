#!/usr/bin/env python3
"""멘토가 만든 결과물 폴더를 제출 구조(game/ · assets/ · sessions/ · video/)로 나눠 복사하고,
PROCESS.md·SUBMISSION.json 초안을 만든 뒤 제출물 검사까지 돌린다. 표준 라이브러리만 쓴다.

- 원본 폴더는 읽기만 한다. 옮기거나 지우지 않고 복사만 한다.
- 글 파일은 복사하면서 개인정보·키를 지운다(check_submission.py와 같은 규칙).
- 이미지는 사진 정보(EXIF·찍은 위치)를 빼고 복사한다(PNG·JPEG).
- 받지 않는 파일(.blend·.rbxl·.rbxm·압축·실행 파일·숨은 파일 등)은 복사하지 않고 이유를 알려 준다.
- 이미 있는 파일은 덮어쓰지 않는다. 바꾸려면 --force.
- 올리기(git push)는 하지 않는다. 멘토가 확인한 뒤 직접 올린다.

사용
  python3 scripts/organize.py <결과물 폴더> [<폴더> ...] [--notes <메모·스크린샷 폴더>] [--video <영상>]
         [--nickname 닉네임] [--tool VARCO|Blender|기타] [--tool-other 도구이름] [--game-url 주소]
         [--one-line 한줄소개] [--hours 시간] [--repo .] [--force] [--dry-run]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # scripts/__pycache__를 만들지 않는다(검사에 걸린다)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_submission as cs  # noqa: E402  검사 규칙·개인정보 규칙을 그대로 쓴다

GAME_EXT = {".rbxlx", ".luau", ".lua", ".toml", ".json", ".yml", ".yaml", ".csv"}
TEXT_NOTE = {".md", ".txt"}
ASSET_EXT = cs.IMAGES | cs.MODELS_TEXT | cs.MODELS_BIN
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
NOTE_HINTS = ("memo", "메모", "note", "노트", "기록", "screenshot", "스크린샷", "캡처", "capture", "session")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", "out", ".harness", "raw"}
WHY_NOT = {
    ".blend": "Blender 원본은 받지 않는다 — Blender에서 File > Export > FBX(.fbx)나 glTF(.glb)로 내보내 다시 넣으세요",
    ".blend1": "Blender 자동 백업 파일",
    ".rbxl": "바이너리 플레이스는 받지 않는다 — Studio에서 File > Save to File As로 .rbxlx(XML)로 저장하세요",
    ".rbxm": "바이너리 모델은 받지 않는다 — Studio에서 Save to File로 .rbxmx(XML)로 저장하세요",
}
SECRET_NAMES = (".env", "id_rsa", "id_ed25519", ".pem", ".key", ".p12", "credentials", "secret", "token", "cookie")

PROCESS_HEADER = "# 만든 과정\n"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ── 사진 정보 빼기 ─────────────────────────────────────────────────
def strip_png(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data
    out, pos = [data[:8]], 8
    while pos + 12 <= len(data):
        n = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        chunk = data[pos:pos + 12 + n]
        if kind not in (b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME"):
            out.append(chunk)
        pos += 12 + n
        if kind == b"IEND":
            break
    return b"".join(out)


def strip_jpeg(data):
    if not data.startswith(b"\xff\xd8"):
        return data
    out, pos = [b"\xff\xd8"], 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            return data  # 구조가 예상과 다르면 손대지 않는다(검사기가 따로 본다)
        marker = data[pos + 1]
        if marker == 0xFF:
            pos += 1
            continue
        if marker == 0xDA:  # 그림 데이터 시작 — 나머지는 그대로
            out.append(data[pos:])
            return b"".join(out)
        n = int.from_bytes(data[pos + 2:pos + 4], "big")
        seg = data[pos:pos + 2 + n]
        # APP1(EXIF·XMP), APP13(IPTC), COM(주석)을 뺀다. APP0·APP2(색 정보)·APP14는 둔다
        if marker not in (0xE1, 0xED, 0xFE):
            out.append(seg)
        pos += 2 + n
    return data


def clean_image(data, ext):
    if ext == ".png":
        return strip_png(data)
    if ext in (".jpg", ".jpeg"):
        return strip_jpeg(data)
    return data


# ── 분류 ──────────────────────────────────────────────────────────
def classify(path, src_root, notes_mode):
    """(목적지 폴더, 이유) — 목적지가 None이면 복사하지 않는다."""
    name = path.name
    ext = path.suffix.lower()
    low = name.lower()
    parts = path.relative_to(src_root).parts
    if any(x.startswith(".") for x in parts):
        return None, "숨은 파일·폴더"
    if any(h in low for h in SECRET_NAMES):
        return None, "키·비밀값 파일로 보인다"
    if cs.bad_name(name):
        return None, "이름에 보이지 않는 글자가 있다"
    inner = ["." + s for s in name.lower().split(".")[1:-1]]
    if ext in cs.BAD_EXT_PARTS or any(x in cs.BAD_EXT_PARTS for x in inner):
        return None, "실행 파일·압축 파일은 받지 않는다"
    if ext in WHY_NOT:
        return None, WHY_NOT[ext]
    if ext in VIDEO_EXT:
        return "video", "영상 후보"
    lowpath = "/".join(parts).lower()
    if notes_mode or any(h in lowpath for h in NOTE_HINTS):
        if ext in TEXT_NOTE or ext in cs.IMAGES:
            return "sessions", "작업 기록·메모"
    if ext in ASSET_EXT:
        return "assets", "에셋"
    if ext in GAME_EXT:
        return "game", "게임 파일"
    if ext in TEXT_NOTE:
        return "game", "게임 설명 글"
    return None, f"받지 않는 형식({ext or '확장자 없음'})"


def walk(src):
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if any(x in SKIP_DIRS for x in rel.parts[:-1]):
            continue
        if p.is_symlink():
            yield p, "symlink"
        elif p.is_file():
            yield p, "file"


def plan_copies(sources, notes_dirs):
    plan, skipped, videos = [], [], []
    multi = len(sources) > 1   # 결과물 폴더가 여럿이면 폴더 이름으로 한 단계 나눈다
    for src, notes_mode in [(s, False) for s in sources] + [(n, True) for n in notes_dirs]:
        for p, kind in walk(src):
            r = p.relative_to(src)
            if not notes_mode and any(n == p or n in p.parents for n in notes_dirs):
                continue   # --notes로 따로 준 폴더는 거기서 한 번만 복사한다
            if kind == "symlink":
                skipped.append((p, "심볼릭 링크"))
                continue
            dest, why = classify(p, src, notes_mode)
            if dest is None:
                skipped.append((p, why))
                continue
            if p.stat().st_size > cs.MAX_FILE and dest != "video":
                skipped.append((p, f"{p.stat().st_size // cs.MB}MB — 파일당 {cs.MAX_FILE // cs.MB}MB 초과"))
                continue
            if dest == "video":
                videos.append(p)
                continue
            sub = Path(src.name) / r if (multi or notes_mode) else r
            plan.append((p, Path(dest) / sub, dest))
    return plan, skipped, videos


def copy_one(src, dest, top, force):
    """돌려주는 값: '복사' | '같음' | '건너뜀(이미 있음)'"""
    ext = src.suffix.lower()
    raw = src.read_bytes()
    if ext in cs.IMAGES:
        data = clean_image(raw, ext)
    elif ext in TEXT_NOTE | GAME_EXT | cs.MODELS_TEXT or (ext == ".fbx" and not raw.startswith(b"Kaydara FBX Binary")
                                                         and b"\x00" not in raw[:4096]):
        text = cs.decode_text(raw)
        if text is None:
            text = raw.decode("utf-16", errors="replace")
        data = cs.scrub(text, in_game=(top != "sessions" and ext not in TEXT_NOTE)).encode("utf-8")
        if text.endswith("\n") and not data.endswith(b"\n"):
            data += b"\n"
    else:
        data = raw
    if dest.exists():
        if dest.read_bytes() == data:
            return "같음"
        if not force:
            return "건너뜀(이미 있음)"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return "복사"


# ── 초안 ──────────────────────────────────────────────────────────
def kind_of(p):
    ext = p.suffix.lower()
    if ext in cs.IMAGES:
        return "이미지"
    if ext == ".rbxmx":
        return "로블록스 모델"
    if ext in cs.MODELS_TEXT | cs.MODELS_BIN:
        return "3D 모델"
    return "설명 글"


def process_draft(repo, tool):
    assets = sorted(p for p in (repo / "assets").rglob("*") if p.is_file()) if (repo / "assets").is_dir() else []
    games = sorted(p for p in (repo / "game").rglob("*") if p.is_file()) if (repo / "game").is_dir() else []
    rows = "\n".join(f"| `{p.relative_to(repo).as_posix()}` | {kind_of(p)} | (여기에 어떻게 만들었나) | (여기에 게임에서 어디에 쓰나) |"
                     for p in assets if kind_of(p) != "설명 글") or "| (여기에 파일) | | | |"
    game_list = "\n".join(f"- `{p.relative_to(repo).as_posix()}`" for p in games[:15])
    if len(games) > 15:
        game_list += f"\n- 그 밖에 {len(games) - 15}개"
    tool_line = f"주로 쓴 도구: {tool}" if tool else "주로 쓴 도구: (여기에 VARCO / Blender / 기타)"
    return f"""{PROCESS_HEADER}
## 무엇을 만들었나
(여기에 어떤 게임인지 한두 문장)

## 어떤 도구로 만들었나
{tool_line}

(여기에 기본 파트 조립, Blender, VARCO를 각각 어디에 썼는지)

게임 파일:
{game_list or "- (여기에 game/ 파일)"}

## 에셋 목록과 용도
| 파일 | 종류 | 어떻게 만들었나 | 게임에서 어디에 쓰나 |
|---|---|---|---|
{rows}

## 직접 플레이해 본 소감
(여기에 직접 해 보니 재미있던 점, 어색하거나 고치고 싶은 점)

## 막힌 곳과 푼 방법
(여기에 막힌 순간마다 무엇이 문제였고 어떻게 풀었는지)

## 아이에게 알려 주고 싶은 것
(여기에 행사 당일 아이가 같은 곳에서 막히면 어떻게 도울지)

## 걸린 시간
(여기에 대략)
"""


def is_template_process(text):
    """아직 아무도 손대지 않은 템플릿이면 True(빈 칸만 있음)."""
    body = [l for l in text.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("|")]
    return all("(여기에" in l for l in body)


def ask(question):
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes", "예", "네", "ㅇ")


def write_process(repo, tool, force, dry):
    path = repo / "PROCESS.md"
    if path.exists() and not force:
        old = cs.read_text_file(path) or ""
        if not is_template_process(old) and not ask("PROCESS.md에 이미 쓴 내용이 있습니다. 초안으로 덮어쓸까요?"):
            print("PROCESS.md: 이미 쓴 내용이 있어 그대로 둠(덮어쓰려면 --force)")
            return
    if dry:
        print("PROCESS.md: 초안을 만들 예정")
        return
    path.write_text(process_draft(repo, tool), encoding="utf-8")
    print("PROCESS.md: 초안 작성 — '(여기에 …)' 칸을 직접 채워 주세요")


FIELDS = ("nickname", "tool", "tool_other", "one_line", "roblox_game_url", "hours_spent", "video")


def write_submission(repo, given, force, dry):
    path = repo / "SUBMISSION.json"
    meta = {}
    if path.exists():
        try:
            meta = json.loads(cs.read_text_file(path) or "{}")
            meta = meta if isinstance(meta, dict) else {}
        except json.JSONDecodeError:
            if not (force or ask("SUBMISSION.json 형식이 깨졌습니다. 새로 만들까요?")):
                print("SUBMISSION.json: 형식이 깨져 그대로 둠(새로 만들려면 --force)")
                return
    if not str(meta.get("coding_ai", "")).strip():
        meta.pop("coding_ai", None)   # 예전 템플릿의 빈 칸은 정리한다
    out = {k: meta.get(k, "") for k in FIELDS}
    out.update({k: v for k, v in meta.items() if k not in out})
    out["video"] = out.get("video") or "video/play.mp4"
    kept = []
    for k, v in given.items():
        if not v:
            continue
        if str(out.get(k, "")).strip() and out[k] != v and not force:
            kept.append(k)
            continue
        out[k] = v
    if kept:
        print(f"SUBMISSION.json: 이미 값이 있는 칸은 그대로 둠({', '.join(kept)}) — 바꾸려면 --force")
    if dry:
        print("SUBMISSION.json: 빈 칸을 채울 예정")
        return
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    empty = [k for k in ("nickname", "tool", "one_line", "roblox_game_url") if not str(out.get(k, "")).strip()]
    print("SUBMISSION.json: 저장" + (f" — 아직 빈 칸: {', '.join(empty)}" if empty else ""))


def main():
    ap = argparse.ArgumentParser(description="결과물 폴더를 제출 구조로 나눠 복사하고 검사한다(원본은 그대로 둔다)")
    ap.add_argument("sources", nargs="*", help="게임·에셋이 든 폴더(여러 개 가능)")
    ap.add_argument("--notes", action="append", default=[], help="작업 메모·스크린샷 폴더(통째로 sessions/로)")
    ap.add_argument("--video", help="플레이 영상 파일(prepare_video.py로 video/play.mp4를 만든다)")
    ap.add_argument("--repo", default=".", help="제출 레포 폴더(기본: 지금 폴더)")
    ap.add_argument("--nickname"); ap.add_argument("--tool", choices=cs.TOOLS); ap.add_argument("--tool-other")
    ap.add_argument("--game-url"); ap.add_argument("--one-line"); ap.add_argument("--hours")
    ap.add_argument("--force", action="store_true", help="이미 있는 파일·초안·값을 덮어쓴다")
    ap.add_argument("--dry-run", action="store_true", help="무엇을 할지 보여 주기만 한다")
    a = ap.parse_args()

    repo = Path(a.repo).expanduser().resolve()
    if not (repo / "scripts" / "check_submission.py").is_file():
        sys.exit(f"제출 레포가 아닙니다(scripts/check_submission.py 없음): {repo}")
    sources = [Path(s).expanduser().resolve() for s in a.sources]
    notes = [Path(s).expanduser().resolve() for s in a.notes]
    for s in sources + notes:
        if not s.is_dir():
            sys.exit(f"폴더가 없습니다: {s}")
        if s == repo or repo in s.parents or s in repo.parents:
            sys.exit(f"결과물 폴더는 제출 레포 밖에 두세요(겹침): {s}")

    plan, skipped, videos = plan_copies(sources, notes)
    counts = {}
    for src, rel, top in plan:
        result = "복사 예정" if a.dry_run else copy_one(src, repo / rel, top, a.force)
        counts[(top, result)] = counts.get((top, result), 0) + 1
        if result.startswith("건너뜀"):
            print(f"  이미 있어 건너뜀: {rel.as_posix()} (덮어쓰려면 --force)")
    for (top, result), n in sorted(counts.items()):
        print(f"{top}/: {result} {n}개")
    if skipped:
        print(f"복사하지 않은 파일 {len(skipped)}개:")
        for p, why in skipped[:40]:
            print(f"  - {p.name}: {why}")
        if len(skipped) > 40:
            print(f"  … 그 밖에 {len(skipped) - 40}개")

    video = Path(a.video).expanduser() if a.video else (videos[0] if len(videos) == 1 else None)
    if video is None and len(videos) > 1:
        print("영상 후보가 여러 개입니다. --video로 하나를 고르세요:")
        for v in videos:
            print(f"  - {v}")
    if video is not None:
        play = repo / "video" / "play.mp4"
        if play.exists() and not a.force:
            print("video/play.mp4: 이미 있어 그대로 둠(다시 만들려면 --force)")
        elif a.dry_run:
            print(f"video/play.mp4: {video.name}로 만들 예정")
        else:
            r = subprocess.run([sys.executable, str(repo / "scripts" / "prepare_video.py"), str(video), "--out", str(play)])
            if r.returncode != 0:
                print("영상 만들기 실패 — 위 메시지를 확인하세요")

    write_submission(repo, {"nickname": a.nickname, "tool": a.tool, "tool_other": a.tool_other,
                            "roblox_game_url": a.game_url, "one_line": a.one_line, "hours_spent": a.hours},
                     a.force, a.dry_run)
    tool = a.tool
    if not tool:
        try:
            tool = json.loads(cs.read_text_file(repo / "SUBMISSION.json") or "{}").get("tool", "")
        except (json.JSONDecodeError, OSError, AttributeError):
            tool = ""
    write_process(repo, tool, a.force, a.dry_run)

    if a.dry_run:
        print("\n(--dry-run: 아무것도 바꾸지 않았습니다)")
        return 0
    print("\n── 제출물 검사 ──")
    res = cs.check(repo)
    for w in res["warnings"]:
        print(f"  주의: {w}")
    for pr in res["problems"]:
        print(f"  문제: {pr}")
    print("통과" if res["passed"] else f"문제 {len(res['problems'])}건 — 고친 뒤 python3 scripts/check_submission.py . 로 다시 검사하세요")
    print("\n아직 올리지 않았습니다. sessions/·PROCESS.md·assets/를 직접 열어 보고, 실명·얼굴·회사명 같은 것이 없는지 "
          "확인한 뒤 올려 주세요(README의 '올리기' 참고).")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
