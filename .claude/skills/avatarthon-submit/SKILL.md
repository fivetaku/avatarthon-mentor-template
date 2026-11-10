---
name: avatarthon-submit
description: 아바타톤 로블록스편 멘토 사전 과제를 이 레포에 정리해 제출한다 — 게임 소스, 플레이 영상(압축), AI와 나눈 대화 기록(개인정보 제거), 과정 정리를 모으고 검사한 뒤 멘토 확인을 받아 공개 레포에 올린다. 트리거 — "아바타톤 제출해줘", "멘토 과제 제출", "제출 정리해줘", "avatarthon submit".
---

# 아바타톤 멘토 과제 제출

이 레포는 멘토 한 사람의 제출함이다. 끝나면 공개 레포 링크 하나를 신청서에 붙인다.
모든 단계는 이 레포 폴더에서 한다. 사람에게 묻는 것은 아래 "물어볼 것" 네 가지와 마지막 올리기 확인뿐이다.

## 지킬 것

- 개인정보·비밀값을 올리지 않는다. 대화 기록은 반드시 `scripts/export_sessions.py`로 옮긴다(직접 복사 금지).
- 실행 파일·압축 파일·원본 영상은 넣지 않는다. 영상은 `scripts/prepare_video.py`가 다시 만든 `video/play.mp4` 하나만.
- `scripts/check_submission.py`가 통과하기 전에는 커밋하지 않는다. 검사기를 고쳐서 통과시키지 않는다.
- 푸시는 멘토가 "올려"라고 확인한 뒤에만 한다.

## 물어볼 것 (처음에 한 번에)

1. 게임을 만든 폴더 경로(로컬). 웹 채팅에서 만들었으면 "웹"이라고 답하게 한다.
2. 플레이 영상 파일 경로(1~3분, 말로 설명한 영상).
3. 로블록스 게임 주소(비공개여도 된다, `https://www.roblox.com/games/...`).
4. 닉네임(실명 불필요)과 쓴 코딩 AI 이름.

## 순서

1. **게임 소스**: 게임 폴더에서 소스만 `game/`에 복사한다. 로컬 폴더가 없으면(웹에서 만든 경우) Roblox Studio에서 게임을 열어 "File > Save to File As"로 `.rbxlx`(XML) 파일을 저장해 `game/`에 넣게 한다. 허용: `.luau .lua .json .toml .md .txt .yml .rbxlx .rbxmx`와 이미지. `.git`, `node_modules`, 빌드 산출물, `.env`, 키 파일, `.rbxl`(바이너리 플레이스)은 빼고, 빼야 할 것이 애매하면 멘토에게 목록을 보여 준다.
2. **영상**: `python3 scripts/prepare_video.py "<영상 경로>"` → `video/play.mp4`.
3. **대화 기록**:
   - `python3 scripts/export_sessions.py find --game-dir "<게임 폴더>"`로 후보를 찾는다.
   - 목록을 멘토에게 보여 주고 이 게임을 만든 대화만 고르게 한 뒤 `python3 scripts/export_sessions.py export <고른 경로들> --out sessions`.
   - 웹 채팅은 멘토가 대화를 텍스트로 복사해 `raw/chat.txt`에 넣게 하고 `python3 scripts/export_sessions.py paste raw/chat.txt --tool web-chat --out sessions`.
   - 만든 `sessions/*.md`를 훑어 지워지지 않은 개인정보(실명, 회사명, 집 주소, 다른 사람 이름 등 규칙으로 못 잡는 것)가 보이면 `[삭제]`로 바꾸고 멘토에게 바꾼 곳을 알린다.
4. **과정 정리**: 대화 기록을 바탕으로 `PROCESS.md`의 "(여기에 …)" 칸을 초안으로 채운다. 첫 지시문은 기록에서 그대로 옮기고, 막힌 곳은 실제로 막혔던 장면만 쓴다. 멘토에게 보여 주고 고칠 곳을 받는다.
5. **SUBMISSION.json**: 닉네임, 코딩 AI, 한 줄 소개(one_line), 게임 주소, 걸린 시간을 채운다.
6. **검사**: `python3 scripts/check_submission.py .` — 문제가 나오면 원인을 고치고 다시 돌린다. 개인정보 발견은 해당 줄을 `[삭제]`로 바꾼다.
7. **확인**: 올라갈 파일 목록(`git status --short`)과 각 대화 기록 앞부분 몇 줄, 영상 크기를 보여 주고 "공개 레포에 올립니다. 올릴까요?"라고 묻는다.
8. **올리기**: 확인을 받으면
   ```
   git add -A && git commit -m "아바타톤 멘토 과제 제출"
   git push
   ```
   원격이 없으면(템플릿을 내려받기만 한 경우) `gh repo create avatarthon-mentor --public --source . --push`. `gh`가 없으면 GitHub에서 빈 공개 레포를 만들어 주소를 받은 뒤 `git remote add origin <주소> && git push -u origin HEAD`.
9. **마무리**: 레포 주소(`gh repo view --json url -q .url` 또는 원격 주소)를 알려 주고 "이 주소를 신청서의 '제출 레포 링크' 칸에 붙여 주세요"로 끝낸다. GitHub Actions의 "제출물 검사"가 초록색인지 함께 확인하게 한다.
