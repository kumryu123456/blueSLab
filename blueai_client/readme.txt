blueai_client/
├── main.py                    # 애플리케이션 진입점
├── ui/
│   ├── main_window.py         # 메인 GUI 구현
│   ├── system_tray.py         # 시스템 트레이 기능
│   └── widgets/               # 커스텀 UI 위젯
│       ├── command_input.py   # 명령어 입력 위젯
│       ├── log_viewer.py      # 로그 표시 위젯
│       └── task_status.py     # 작업 상태 표시 위젯
├── automation/
│   ├── browser_manager.py     # Playwright 브라우저 관리
│   ├── task_parser.py         # 명령어 파싱 및 작업 선택
│   ├── tasks/                 # 자동화 작업 모듈
│   │   ├── base_task.py       # 기본 작업 클래스
│   │   ├── web_search.py      # 웹 검색 작업
│   │   ├── data_extraction.py # 데이터 추출 작업
│   │   ├── nara_marketplace.py # 나라장터 작업
│   │   ├── news_summary.py    # 뉴스 요약 작업
│   │   └── file_operations.py # 파일 관련 작업
│   └── utils.py               # 유틸리티 함수
├── api/
│   ├── client.py              # 향후 서버 API 클라이언트
│   ├── mock_server.py         # 테스트용 목업 서버
│   └── models.py              # 데이터 모델
├── config/
│   ├── settings.py            # 설정
│   └── logging.py             # 로깅 설정
└── cli.py                     # 명령줄 인터페이스





# BlueAI 클라이언트

BlueAI 서버와 통신하여 자동화 작업을 수행하는 Python 클라이언트 애플리케이션입니다.

## 주요 기능

- **자연어 명령어 처리**: 자연어로 입력된 명령어를 해석하여 적절한 자동화 작업 실행
- **웹 자동화**: Playwright를 사용한 웹사이트 자동화 작업 수행
- **데이터 추출**: 웹 페이지에서 데이터를 추출하여 Excel 파일로 저장
- **GUI 및 CLI 지원**: 그래픽 인터페이스와 명령줄 인터페이스 모두 지원
- **서버 연동 대비**: 향후 BlueAI 서버와의 통합을 위한 확장성 제공

## 시스템 요구사항

- Python 3.8 이상
- 지원 운영체제: Windows, macOS, Linux

## 설치 방법

1. 저장소 복제
   ```
   git clone https://github.com/yourusername/blueai-client.git
   cd blueai-client
   ```

2. 가상 환경 생성 및 활성화
   ```
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. 필요한 패키지 설치
   ```
   pip install -r requirements.txt
   ```

4. Playwright 브라우저 설치
   ```
   playwright install
   ```

## 사용 방법

### GUI 모드

GUI 모드로 실행하려면:

```
python main.py
```

추가 옵션:
- `--headless`: 브라우저를 화면에 표시하지 않고 실행
- `--server URL`: BlueAI 서버 URL 설정 (기본값: 없음, 독립 모드로 실행)
- `--log-level LEVEL`: 로깅 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### CLI 모드

명령줄에서 직접 작업을 실행하려면:

```
python cli.py "나라장터에서 RPA 공고를 검색해줘"
```

대화형 모드로 실행:

```
python cli.py --interactive
```

명령어 예시:
- `나라장터에서 RPA 공고를 검색해줘`
- `오늘 뉴스를 요약해주고 감정 분석해서 음악 추천해줘`
- `날씨 정보를 이미지로 저장해줘`

## 폴더 구조

```
blueai_client/
├── main.py                    # 애플리케이션 진입점
├── cli.py                     # 명령줄 인터페이스
├── ui/                        # UI 관련 모듈
├── automation/                # 자동화 작업 관련 모듈
├── api/                       # API 클라이언트 관련 모듈
└── config/                    # 설정 관련 모듈
```

## 개발자 가이드

새로운 자동화 작업을 추가하려면:

1. `automation/tasks/` 디렉토리에 새로운 Python 파일 생성
2. `BaseTask` 클래스를 상속하는 작업 클래스 구현
3. 작업과 관련된 키워드와 매개변수 정의
4. `execute()` 메서드 구현

## 라이선스

[MIT 라이선스](LICENSE)

## 연락처

문제가 발생하거나 제안 사항이 있으면 GitHub 이슈를 통해 알려주세요.