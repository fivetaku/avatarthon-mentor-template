#!/usr/bin/env python3
"""AI 코딩 도구의 대화 기록을 찾아 개인정보를 지운 마크다운으로 옮긴다.

지원: Claude Code(~/.claude/projects/*/*.jsonl), Codex(~/.codex/sessions/**/rollout-*.jsonl).
웹 채팅은 화면에서 복사한 글을 --paste 파일로 넣는다.

사용
  찾기:   python3 scripts/export_sessions.py find --game-dir <게임 폴더> [--days 60]
  옮기기: python3 scripts/export_sessions.py export <jsonl 경로...> --out sessions/
  붙여넣기: python3 scripts/export_sessions.py paste <복사한 글.txt> --out sessions/ --tool web-chat
  지우기만: python3 scripts/export_sessions.py scrub <파일.md>

옮긴 기록에는 사람이 쓴 말과 AI의 답, AI가 쓴 도구 이름만 남는다.
도구 실행 결과·파일 내용·시스템 메시지는 옮기지 않는다(개인 파일이 섞이기 쉬워서).
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

HOME = Path.home()

# 바꿔 넣을 꼬리표. check_submission.py가 이 꼬리표는 개인정보로 보지 않는다.
SCRUB_RULES = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[개인키 삭제]"),
    (re.compile(r"_\|WARNING:-DO-NOT-SHARE-THIS[^\s\"']*"), "[로블록스 쿠키 삭제]"),
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"), "[키 삭제]"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}"), "[키 삭제]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "[키 삭제]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[키 삭제]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "[키 삭제]"),
    (re.compile(r"\bxai-[A-Za-z0-9]{20,}"), "[키 삭제]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}"), "Bearer [키 삭제]"),
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd)\b(\s*[:=]\s*)[\"']?[^\s\"']{8,}"), r"\1\2[삭제]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[이메일]"),
    (re.compile(r"(?<!\d)\d{6}-?[1-4]\d{6}(?!\d)"), "[주민번호]"),
    (re.compile(r"(?<!\d)(?:\d{4}[- ]){3}\d{4}(?!\d)"), "[카드번호]"),
    (re.compile(r"(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)"), "[전화번호]"),
    (re.compile(r"/Users/[^/\s]+/"), "/Users/[사용자]/"),
    (re.compile(r"/home/[^/\s]+/"), "/home/[사용자]/"),
    (re.compile(r"([A-Za-z]:\\Users\\)[^\\\s]+\\"), r"\1[사용자]\\"),
    (re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), "[IP]"),
]
SYSTEM_BLOCK = re.compile(r"<(system-reminder|command-[a-z-]+|local-command-[a-z-]+)>.*?</\1>", re.S)


def scrub(text):
    text = SYSTEM_BLOCK.sub("", text)
    for pat, rep in SCRUB_RULES:
        text = pat.sub(rep, text)
    return text.strip()


def _first_cwd(path, limit=40):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = obj.get("cwd") or (obj.get("payload") or {}).get("cwd")
                if cwd:
                    return cwd
    except OSError:
        return None
    return None


def find(game_dir, days):
    game = str(Path(game_dir).expanduser().resolve())
    since = time.time() - days * 86400
    roots = [("claude-code", HOME / ".claude" / "projects", "*/*.jsonl"),
             ("codex", HOME / ".codex" / "sessions", "**/rollout-*.jsonl")]
    found = []
    for tool, base, pattern in roots:
        if not base.is_dir():
            continue
        for p in base.glob(pattern):
            try:
                if p.stat().st_mtime < since:
                    continue
            except OSError:
                continue
            cwd = _first_cwd(p)
            if cwd and (cwd == game or cwd.startswith(game.rstrip("/\\") + ("\\" if "\\" in game else "/"))):
                found.append((p.stat().st_mtime, tool, p))
    found.sort()
    for mtime, tool, p in found:
        print(f"{tool}\t{time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))}\t{p}")
    if not found:
        print("이 게임 폴더에서 연 대화 기록을 찾지 못했다. 다른 폴더에서 작업했다면 그 폴더로 다시 찾거나 paste를 쓰세요.",
              file=sys.stderr)
    return found


def _claude_turns(obj):
    kind = obj.get("type")
    if kind not in ("user", "assistant") or obj.get("isMeta") or obj.get("isSidechain"):
        return []
    msg = obj.get("message") or {}
    content = msg.get("content")
    role = "나" if kind == "user" else "AI"
    out = []
    if isinstance(content, str):
        out.append((role, content))
    elif isinstance(content, list):
        for c in content:
            t = c.get("type")
            if t == "text":
                out.append((role, c.get("text", "")))
            elif t == "tool_use":
                out.append(("도구", c.get("name", "?")))
            # tool_result·image·thinking은 옮기지 않는다
    return out


def _codex_turns(obj):
    if obj.get("type") != "response_item":
        return []
    p = obj.get("payload") or {}
    if p.get("type") == "message" and p.get("role") in ("user", "assistant"):
        role = "나" if p["role"] == "user" else "AI"
        texts = [c.get("text", "") for c in p.get("content", []) if c.get("type") in ("input_text", "output_text")]
        return [(role, "\n".join(texts))]
    if p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
        return [("도구", p.get("name") or p.get("type"))]
    return []


def to_markdown(path, tool):
    turns = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            turns += _claude_turns(obj) if tool == "claude-code" else _codex_turns(obj)
    lines, tool_run = [], []

    def flush_tools():
        if tool_run:
            lines.append(f"> AI가 쓴 도구: {', '.join(tool_run)}\n")
            tool_run.clear()

    for role, text in turns:
        if role == "도구":
            tool_run.append(text)
            continue
        text = scrub(text)
        if not text:
            continue
        # Codex가 넣는 환경 안내문은 사람이 쓴 말이 아니다
        if role == "나" and (text.startswith("<environment_context>") or text.startswith("# AGENTS.md")):
            continue
        flush_tools()
        lines.append(f"**{role}**\n\n{text}\n")
    flush_tools()
    return "\n".join(lines)


def detect_tool(path):
    s = str(path)
    if "/.codex/" in s or Path(s).name.startswith("rollout-"):
        return "codex"
    return "claude-code"


def export(paths, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, p in enumerate(paths, 1):
        p = Path(p)
        tool = detect_tool(p)
        body = to_markdown(p, tool)
        if not body.strip():
            print(f"건너뜀(대화 없음): {p.name}", file=sys.stderr)
            continue
        dest = out / f"session-{i:02d}-{tool}.md"
        dest.write_text(f"# 대화 기록 {i} ({tool})\n\n"
                        "개인정보·키·내 컴퓨터 경로는 지웠다. 도구 실행 결과는 옮기지 않았다.\n\n" + body,
                        encoding="utf-8")
        written.append(dest)
        print(f"저장: {dest} ({len(body):,}자)")
    return written


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find"); f.add_argument("--game-dir", required=True); f.add_argument("--days", type=int, default=60)
    e = sub.add_parser("export"); e.add_argument("paths", nargs="+"); e.add_argument("--out", default="sessions")
    pa = sub.add_parser("paste"); pa.add_argument("file"); pa.add_argument("--out", default="sessions"); pa.add_argument("--tool", default="web-chat")
    s = sub.add_parser("scrub"); s.add_argument("file")
    a = ap.parse_args()
    if a.cmd == "find":
        find(a.game_dir, a.days)
    elif a.cmd == "export":
        export(a.paths, a.out)
    elif a.cmd == "paste":
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        n = len(list(out.glob("session-*.md"))) + 1
        dest = out / f"session-{n:02d}-{a.tool}.md"
        body = scrub(Path(a.file).read_text(encoding="utf-8", errors="replace"))
        dest.write_text(f"# 대화 기록 {n} ({a.tool}, 붙여넣기)\n\n{body}\n", encoding="utf-8")
        print(f"저장: {dest}")
    elif a.cmd == "scrub":
        p = Path(a.file)
        p.write_text(scrub(p.read_text(encoding="utf-8", errors="replace")) + "\n", encoding="utf-8")
        print(f"정리: {p}")


if __name__ == "__main__":
    main()
