# Unity Free Asset

Unity Asset Store가 매주 주는 **Publisher of the Week 무료 에셋**을 자동으로 내 계정에 담아 주는 Windows용 스크립트입니다.
매주 사이트 들어가서 쿠폰 넣고 결제하는 걸 까먹어서 놓치는 사람을 위해 만들었습니다.

- 매일 정오에 혼자 돌면서 이번 주 무료 에셋을 확인하고, 아직 안 담았으면 담습니다.
- 쿠폰 적용 후 결제 금액이 **$0.00일 때만** 결제 버튼을 누릅니다. 돈이 나갈 상황이면 멈추고 알려 줍니다.
- 결과는 Windows 알림과 로그로 남습니다.

실제 파일 다운로드는 Unity 에디터의 Package Manager > My Assets 에서 하면 됩니다. 이 스크립트는 "계정에 담기"까지만 합니다.

## 필요한 것
- Windows 10/11
- [Python 3.10 이상](https://www.python.org/downloads/) — 설치할 때 **"Add python.exe to PATH"** 체크
- Google Chrome
- Unity 계정 (Asset Store에서 결제 정보가 한 번은 등록돼 있어야 체크아웃이 통과됩니다. $0이라 청구는 없습니다.)

## 설치 (한 번만)
1. 이 저장소를 내려받습니다. `Code > Download ZIP` 후 압축을 풀거나:
   ```
   git clone https://github.com/yogain416/unity-free-asset.git
   ```
2. 폴더 안의 **`setup.bat`** 을 더블클릭합니다.
   - 가상환경과 Playwright(Chrome 자동화 도구)를 설치합니다.
   - Chrome 창이 하나 뜨면 **Unity 계정으로 로그인**하세요. Asset Store 페이지로 돌아오면 자동으로 저장되고 닫힙니다. 창을 직접 닫지 마세요.
   - 작업 스케줄러에 "Unity Free Asset"이 등록되고, 바로 한 번 실행해 봅니다.
3. 콘솔에 `성공` 또는 `이미 보유 중` 이 보이면 끝입니다.

이후로는 매일 12:00에 자동으로 돕니다. PC가 꺼져 있었으면 다음에 켜졌을 때 실행됩니다.

## 로그인이 풀렸을 때
"로그인 세션이 만료됐습니다" 알림이 오면 **`login.bat`** 을 더블클릭해 다시 로그인하면 됩니다.
Unity의 로그인 쿠키는 브라우저를 닫으면 사라지는 종류라 `auth.json`에 따로 보관하는데, 몇 주 지나면 서버 쪽에서 만료됩니다.

## 동작 순서
1. [세일 페이지](https://assetstore.unity.com/publisher-sale)에서 이번 주 무료 에셋 링크와 쿠폰 코드를 읽습니다.
2. 이미 담은 에셋(`state.json`)이거나 이미 보유 중("Open in Unity" 버튼)이면 그냥 끝냅니다.
3. 장바구니 → Checkout → 쿠폰 적용 → "To pay now"가 $0.00인지 확인 → EULA 동의 체크 → Pay now.
4. 에셋 페이지에 "Open in Unity"가 뜨는지 확인하고 기록합니다.

## 문제가 생기면
- `logs/run.log` 에 무엇을 하다 멈췄는지 적혀 있고, `logs/fail-*.png` 에 그 순간 화면이 저장됩니다.
- Unity가 사이트 구조를 바꾸면 깨질 수 있습니다. 로그와 스크린샷을 첨부해 이슈를 올려 주세요.

## 수동 실행
```
.venv\Scripts\python claim.py            # 지금 바로 담기 (창 없이)
.venv\Scripts\python claim.py --headed   # 브라우저를 보면서
.venv\Scripts\python claim.py --login    # 다시 로그인 (= login.bat)
```

스케줄 해제:
```
powershell -Command "Unregister-ScheduledTask -TaskName 'Unity Free Asset' -Confirm:$false"
```

## 파일
| 파일 | 역할 |
|---|---|
| `claim.py` | 본체 |
| `setup.bat` | 처음 설치 (venv → Playwright → 로그인 → 스케줄 등록) |
| `login.bat` | 로그인만 다시 |
| `register_task.ps1` | 작업 스케줄러 등록 |
| `auth.json`, `profile/` | **내 로그인 정보. 절대 공유하거나 커밋하지 마세요** (.gitignore에 포함) |
| `state.json`, `logs/` | 담은 에셋 기록, 실행 로그 |

## 주의
- 개인 사용 목적의 브라우저 자동화입니다. Unity Asset Store 약관은 각자 확인하세요.
- 스크립트는 총액이 $0일 때만 결제하지만, 결제 정보가 등록된 계정을 자동화하는 것이므로 코드를 한 번 읽어 보고 쓰시길 권합니다.

## License
MIT
