# 이 레포에서 일하는 AI에게

이 레포는 아바타톤 로블록스편 멘토 과제 제출함이다.
사용자가 "아바타톤 제출해줘", "제출 정리해줘"라고 하면 `.claude/skills/avatarthon-submit/SKILL.md`를 읽고 그 순서를 그대로 따른다.
Codex·Claude Code 어느 쪽이든 같은 절차다.

핵심 규칙
- 대화 기록은 `scripts/export_sessions.py`로만 옮긴다(개인정보 제거).
- 영상은 `scripts/prepare_video.py`로 다시 만든 `video/play.mp4` 하나만.
- `python3 scripts/check_submission.py .`가 통과하기 전에는 커밋하지 않고, 검사기를 고쳐서 통과시키지 않는다.
- 푸시는 사용자가 확인한 뒤에만.
