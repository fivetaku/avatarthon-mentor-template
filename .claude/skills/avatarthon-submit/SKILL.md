---
name: avatarthon-submit
description: 아바타톤 로블록스편 멘토 사전 과제를 이 레포에 정리해 제출한다 — 멘토가 VARCO·Blender로 직접 만든 게임 파일과 에셋, 플레이 영상(압축), 작업 기록(개인정보 제거), 과정 정리를 모아 검사한 뒤 멘토 확인을 받아 공개 레포에 올린다. 게임을 만들거나 고치지는 않는다. 트리거 — "아바타톤 제출해줘", "멘토 과제 제출", "제출 정리해줘", "avatarthon submit".
---

# 아바타톤 멘토 과제 제출

이 레포는 멘토 한 사람의 제출함이다. 끝나면 공개 레포 링크 하나를 구글 폼에 붙인다.
멘토는 게임과 에셋을 이미 만들고 직접 플레이해 봤다. 여기서는 결과물을 분석·정리만 한다. 게임을 새로 만들거나 고치지 않는다.
모든 단계는 이 레포 폴더에서 한다. 사람에게 묻는 것은 아래 "물어볼 것"과 마지막 올리기 확인뿐이다.

## 지킬 것

- 멘토의 원본 폴더는 읽기만 한다. 결과물은 `scripts/organize.py`로 복사한다(옮기거나 지우지 않는다).
- 개인정보·비밀값을 올리지 않는다. AI 대화 기록은 반드시 `scripts/export_sessions.py`로 옮긴다(직접 복사 금지).
- 실행 파일·압축 파일·원본 영상·`.blend`·`.rbxl`·`.rbxm`은 넣지 않는다. 영상은 `video/play.mp4` 하나만.
- `game/`과 `assets/` 둘 다 비어 있으면 안 된다.
- `scripts/check_submission.py`가 통과하기 전에는 커밋하지 않는다. 검사기를 고쳐서 통과시키지 않는다.
- 푸시는 멘토가 "올려"라고 확인한 뒤에만 한다.

## 물어볼 것 (처음에 한 번에)

1. 결과물 폴더 경로(게임 파일과 에셋이 든 폴더, 여러 개 가능). 게임 파일이 없으면 Roblox Studio에서 "File > Save to File As"로 `.rbxlx`를 저장하게 한다.
2. 작업 메모·스크린샷 폴더(VARCO·Blender 화면, 넣은 그림과 결과). 없으면 "없음".
3. 플레이 영상 파일 경로(1~3분, 말로 설명한 영상).
4. 로블록스 게임 주소(비공개여도 된다, `https://www.roblox.com/games/...`), 닉네임(실명 불필요), 주로 쓴 도구("VARCO"·"Blender"·"기타" 중 하나, 기타면 도구 이름).

## 순서

1. **나눠 복사**: 먼저 `--dry-run`으로 무엇이 어디로 가는지 보여 준다.
   ```
   python3 scripts/organize.py <결과물 폴더> --notes <메모 폴더> --video <영상> \
       --nickname <닉네임> --tool <VARCO|Blender|기타> [--tool-other <이름>] --game-url <주소> --dry-run
   ```
   멘토가 괜찮다고 하면 `--dry-run`을 빼고 다시 돌린다. "복사하지 않은 파일" 목록에 `.blend`가 있으면 Blender에서 FBX나 GLB로 내보내게 하고, `.rbxl`·`.rbxm`이면 `.rbxlx`·`.rbxmx`로 저장하게 한 뒤 다시 돌린다.
2. **assets 확인**: `assets/`가 비었으면(기본 파트로만 만든 경우) 스튜디오에서 소품을 골라 "Save to File"로 `.rbxmx`를 저장하거나 소품 스크린샷을 찍게 해 결과물 폴더에 넣고 1을 다시 돌린다.
3. **작업 기록**:
   - Claude Code·Codex로 작업한 부분이 있으면 `python3 scripts/export_sessions.py find --game-dir "<게임 폴더>"`로 후보를 찾고, 멘토가 고른 것만 `python3 scripts/export_sessions.py export <경로들> --out sessions`.
   - 웹 채팅은 `raw/chat.txt`에 복사해 두게 하고 `python3 scripts/export_sessions.py paste raw/chat.txt --tool web-chat --out sessions`.
   - VARCO·Blender는 기록 파일이 없다. 메모 폴더(1의 `--notes`)로 들어간 스크린샷과 메모가 그 기록이다. 메모가 없으면 멘토에게 넣은 그림·설명 글·결과를 몇 줄 받아 `raw/memo.txt`에 쓰고 `python3 scripts/export_sessions.py paste raw/memo.txt --tool varco --out sessions`.
   - `sessions/`의 글을 훑어 규칙으로 못 잡은 개인정보(실명, 회사명, 집 주소, 다른 사람 이름)가 보이면 `[삭제]`로 바꾸고 멘토에게 알린다. 스크린샷은 멘토가 직접 확인하게 한다.
4. **결과물 분석·과정 정리**: `game/`·`assets/` 목록과 작업 기록, 멘토 설명을 바탕으로 `PROCESS.md`의 "(여기에 …)" 칸을 초안으로 채운다.
   - 무엇을 어떤 도구로 만들었나: 기본 파트 조립·Blender·VARCO를 어디에 썼는지.
   - 에셋 표: 파일마다 어떻게 만들었고 게임 어디에 쓰는지. 모르는 칸은 지어내지 말고 멘토에게 묻는다.
   - 직접 플레이해 본 소감, 막힌 곳과 푼 방법, 아이에게 알려 주고 싶은 것은 멘토의 말을 옮긴다.
   초안을 보여 주고 고칠 곳을 받는다.
5. **SUBMISSION.json**: 닉네임, `tool`, 한 줄 소개(`one_line`), 게임 주소, 걸린 시간이 다 찼는지 본다. `tool`은 "VARCO"·"Blender"·"기타" 글자 그대로.
6. **검사**: `python3 scripts/check_submission.py .` — 문제가 나오면 원인을 고치고 다시 돌린다. `sessions/`·`PROCESS.md`의 개인정보 발견은 해당 값을 `[삭제]`로 바꾼다. `game/`·`assets/` 파일에서 걸리면 줄을 지우지 말고(파일이 망가진다) 멘토에게 보여 주고, 진짜 키·개인정보면 원본 쪽에서 빼고 다시 내보내게 한다. 윈도우에서 글 파일을 만들면 UTF-8로 저장한다(PowerShell은 `Set-Content -Encoding utf8`).
7. **확인**: 올라갈 파일 목록(`git status --short`), `assets/` 목록, 작업 기록 앞부분 몇 줄, 영상 크기를 보여 주고 "공개 레포에 올립니다. 올릴까요?"라고 묻는다.
8. **올리기**: 확인을 받으면
   ```
   git add -A && git commit -m "아바타톤 멘토 과제 제출"
   git push
   ```
   원격이 없으면(템플릿을 내려받기만 한 경우) `gh repo create avatarthon-mentor --public --source . --push`. `gh`가 없으면 GitHub에서 빈 공개 레포를 만들어 주소를 받은 뒤 `git remote add origin <주소> && git push -u origin HEAD`.
9. **마무리**: 레포 주소(`gh repo view --json url -q .url` 또는 원격 주소)를 알려 주고 "이 주소를 구글 폼의 레포 링크 칸에 붙여 주세요. 마감은 11월 23일입니다"로 끝낸다. GitHub Actions의 "제출물 검사"가 초록색인지 함께 확인하게 한다.
