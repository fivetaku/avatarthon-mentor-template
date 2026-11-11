# 이 레포에서 일하는 AI에게

이 레포는 아바타톤 로블록스편 멘토 과제 제출함이다.
멘토는 VARCO나 Blender로 게임과 에셋을 이미 직접 만들었다. 이 레포에서 하는 일은 그 결과물을 분석·정리해 올리는 것뿐이다.
게임을 새로 만들거나 고치는 일, 만드는 방법을 안내하는 일은 하지 않는다.

사용자가 "아바타톤 제출해줘", "제출 정리해줘"라고 하면 `.claude/skills/avatarthon-submit/SKILL.md`를 읽고 그 순서를 그대로 따른다.
Codex·Claude Code 어느 쪽이든 같은 절차다.

핵심 규칙
- 결과물은 `scripts/organize.py`로 복사한다. 멘토의 원본 폴더는 옮기거나 지우지 않는다.
- 대화 기록은 `scripts/export_sessions.py`로만 옮긴다(개인정보 제거). VARCO·Blender 작업은 스크린샷과 메모로 남긴다.
- 영상은 `scripts/prepare_video.py`로 다시 만든 `video/play.mp4` 하나만.
- `game/`과 `assets/`는 둘 다 비어 있으면 안 된다. `SUBMISSION.json`의 `tool`은 "VARCO"·"Blender"·"기타" 중 하나.
- `python3 scripts/check_submission.py .`가 통과하기 전에는 커밋하지 않고, 검사기를 고쳐서 통과시키지 않는다.
- 푸시는 사용자가 확인한 뒤에만.
