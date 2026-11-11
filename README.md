# 아바타톤 로블록스편 멘토 과제 제출함

아바타톤 로블록스편(2026년 12월 5일 토, 성남 갤러리OA) 멘토 신청용 템플릿입니다.
VARCO나 Blender로 로블록스 게임과 에셋을 직접 만들고, 직접 플레이해 본 뒤, 이 키트로 결과물을 정리해 공개 레포로 올립니다.
만든 레포 주소를 구글 폼에 붙이면 제출이 끝납니다. 마감은 11월 23일입니다.

이 키트는 게임 만드는 법을 알려 주지 않습니다. 이미 만든 결과물을 나누고, 개인정보를 지우고, 검사하는 일만 합니다.

## 흐름

1. **만들기**: 로블록스 스튜디오에서 게임을 만들고 소품(에셋)을 만듭니다.
   기본은 스튜디오의 기본 파트를 조립하는 것이고, 선택으로 Blender 메시나 VARCO 3D를 씁니다.
2. **플레이**: 직접 해 보고 1~3분 플레이 영상을 찍습니다. 말로 설명하며 찍어 주세요.
3. **정리**: 이 키트로 결과물을 나누고 검사해 공개 레포로 올립니다.
4. **등록**: 레포 주소를 구글 폼에 붙입니다.

## 제출물

| 폴더·파일 | 내용 |
|---|---|
| `game/` | 게임 파일. 스튜디오에서 저장한 `.rbxlx`나 Luau 소스. 꼭 있어야 합니다 |
| `assets/` | 만든 에셋. 이미지, `.fbx` `.obj` `.glb` `.gltf`, `.rbxmx`. 꼭 있어야 합니다 |
| `video/play.mp4` | 1~3분 플레이 영상 |
| `sessions/` | 작업 기록. AI 대화 기록, 메모, 스크린샷 |
| `PROCESS.md` | 무엇을 어떤 도구로 만들었나, 에셋 목록과 용도, 플레이 소감, 막힌 곳, 아이에게 알려 줄 것 |
| `SUBMISSION.json` | 닉네임, 쓴 도구(`tool`), 한 줄 소개, 게임 주소 |

`game/`과 `assets/`는 둘 다 있어야 합니다. 하나만 있으면 검사를 통과하지 못합니다.
용량은 파일 하나 50MB, 플레이 영상 50MB, 레포 전체 120MB까지입니다. 넘으면 검사를 통과하지 못하니, 쓰지 않은 시안·옛 버전은 빼고 게임에 실제로 들어간 에셋만 넣어 주세요.
기본 파트만으로 소품을 만들었다면 스튜디오에서 소품을 골라 "Save to File"로 `.rbxmx`를 저장하거나, 소품 스크린샷을 `assets/`에 넣어 주세요.

### SUBMISSION.json의 tool

`tool`에는 아래 셋 중 하나를 글자 그대로 씁니다. 구글 폼의 선택지와 같습니다.

- `"VARCO"`
- `"Blender"`
- `"기타"` — 이때는 `tool_other`에 쓴 도구 이름을 적어 주세요.

둘 다 썼다면 더 많이 쓴 쪽을 고르고, 나머지는 `PROCESS.md`에 적습니다. 빈칸이거나 다른 값(예: `"Unity"`)이면 검사를 통과하지 못합니다.

### assets/에 넣을 수 있는 파일

| 넣을 수 있다 | 넣을 수 없다 |
|---|---|
| `.png` `.jpg` `.jpeg` `.webp` 이미지(텍스처·원화·소품 스크린샷) | `.blend` (Blender 원본) |
| `.fbx` `.obj`(+`.mtl`) `.glb` `.gltf` 3D 모델 | `.rbxm` `.rbxl` (로블록스 바이너리) |
| `.rbxmx` 로블록스 모델(XML) | 압축 파일, 실행 파일 |
| `.md` `.txt` 설명 글 | |

`.blend`를 받지 않는 이유: Blender 원본 파일은 안에 파이썬 스크립트를 넣을 수 있고, 열면 실행될 수 있습니다. 또 바이너리라서 개인정보나 비밀값이 섞였는지 검사기가 글로 읽어 볼 수 없습니다. Blender에서 **File > Export > FBX**나 **glTF 2.0(.glb)**로 내보낸 파일을 넣어 주세요. 로블록스에 올릴 때도 FBX를 씁니다.
같은 이유로 `.rbxm` `.rbxl` 대신 XML 형식인 `.rbxmx` `.rbxlx`로 저장합니다.

## 제출하는 법

1. 이 페이지 위의 **Use this template**으로 내 계정에 공개 레포를 만들고 내 컴퓨터에 받습니다.
   명령으로는 한 줄입니다.
   ```
   gh repo create avatarthon-mentor --template fivetaku/avatarthon-mentor-template --public --clone
   ```
2. 결과물 폴더를 넣고 정리 스크립트를 돌립니다. 원본 폴더는 건드리지 않고 복사만 합니다.
   ```
   python3 scripts/organize.py ~/로블록스결과물 --notes ~/작업메모 --video ~/플레이.mov \
       --nickname 닉네임 --tool VARCO --game-url https://www.roblox.com/games/... --one-line "한 줄 소개"
   ```
   - 파일을 확장자로 나눠 `game/` `assets/` `sessions/`에 복사합니다. `--notes` 폴더는 통째로 `sessions/`로 갑니다.
   - 글 파일의 개인정보·키를 지우고, 이미지의 사진 정보(찍은 위치 등)를 뺍니다.
   - `.blend`처럼 받지 않는 파일은 복사하지 않고 이유를 알려 줍니다.
   - `PROCESS.md`, `SUBMISSION.json` 초안을 만듭니다. 이미 쓴 내용이 있으면 덮어쓰지 않습니다(덮어쓰려면 `--force`).
   - 마지막에 검사를 돌립니다. 무엇을 할지만 보려면 `--dry-run`.
3. `PROCESS.md`의 "(여기에 …)" 칸을 직접 채웁니다. 에셋 표의 "어떻게 만들었나·어디에 쓰나"도 채워 주세요.
4. 다시 검사합니다. `python3 scripts/check_submission.py .`가 "통과"라고 나와야 합니다.
5. 올라갈 파일을 직접 훑어보고 올립니다.
   ```
   git add -A && git commit -m "아바타톤 멘토 과제 제출" && git push
   ```
6. 레포 주소를 구글 폼에 붙입니다. GitHub의 Actions 탭에서 "제출물 검사"가 초록색인지도 확인해 주세요.

Claude Code나 Codex가 있으면 이 폴더에서 "아바타톤 제출해줘"라고 말해도 됩니다. 위 순서대로 정리하고, 올리기 전에 한 번 확인을 받습니다.

## 작업 기록(sessions/) 남기는 법

- **AI와 대화하며 만들었다면**(Claude Code·Codex):
  `python3 scripts/export_sessions.py find --game-dir <게임 폴더>`로 찾고 `python3 scripts/export_sessions.py export <경로들> --out sessions`로 옮깁니다.
- **웹 채팅을 썼다면**: 대화를 복사해 `raw/chat.txt`에 넣고
  `python3 scripts/export_sessions.py paste raw/chat.txt --tool web-chat --out sessions`.
- **VARCO·Blender 기록은 export_sessions로 뽑히지 않습니다.** 두 도구는 대화 기록 파일을 남기지 않기 때문입니다. 대신 이렇게 남겨 주세요.
  - 작업 화면 스크린샷(VARCO에 넣은 그림과 나온 결과, Blender 작업 화면)을 `.png`나 `.jpg`로 모읍니다.
  - 무엇을 했는지 메모를 `.md`나 `.txt`로 씁니다. VARCO에 넣은 설명 글(프롬프트)이 있으면 그대로 옮겨 적습니다.
  - 두 가지를 한 폴더에 모아 `organize.py --notes <폴더>`로 넣거나, 메모만 `python3 scripts/export_sessions.py paste 메모.txt --tool varco --out sessions`로 넣습니다(개인정보를 지우고 넣습니다).
  - 스크린샷 속 이름·이메일·얼굴은 자동으로 지워지지 않습니다. 넣기 전에 직접 확인해 주세요.

## 개인정보와 안전

- 대화 기록은 사람이 쓴 말과 AI의 답, AI가 쓴 도구 이름만 옮깁니다. 도구 실행 결과와 파일 내용은 옮기지 않습니다.
- 이메일, 전화번호, 주민번호, 카드번호, API 키, 로블록스 로그인 쿠키, 내 컴퓨터 사용자 이름이 든 경로는 자동으로 지웁니다.
  실명·회사명처럼 규칙으로 못 잡는 것은 올리기 전에 직접 확인해 주세요.
- 영상은 새 mp4로 다시 만들어 위치 정보 같은 메타데이터를 남기지 않습니다(`scripts/prepare_video.py`).
- 실행 파일, 압축 파일, 원본 영상은 받지 않습니다. 올리면 GitHub Actions의 "제출물 검사"가 확인합니다.
  직접 검사하려면 `python3 scripts/check_submission.py .`

## 필요한 것

Python 3, git, ffmpeg(영상 압축). `gh`(GitHub CLI)가 있으면 편합니다. 코딩 AI는 없어도 됩니다.

문의: gptaku@axwith.com · 본 행사는 Roblox Corporation과 무관한 독립 커뮤니티 행사입니다.
