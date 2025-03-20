BlueAI/                         # 메인 프로젝트 폴더
├── config/                     # 설정 관련 파일
│   ├── __init__.py
│   ├── settings.py              # 시스템 설정 관리
│   ├── logging_config.py        # 로깅 설정
│   └── constants.py             # 상수 값 관리
├── core/                        # 핵심 기능 모듈
│   ├── __init__.py
│   ├── interruption_handler.py  # 광고/팝업 처리
│   ├── plugin_system.py         # 플러그인 시스템
│   ├── settings_manager.py      # 설정 관리
│   ├── workflow_manager.py      # 워크플로우 관리
│   ├── plugins/                 # 플러그인 모음
│   │   ├── __init__.py
│   │   ├── automation/          # 자동화 관련 플러그인
│   │   ├── interruption/        # 인터럽션 처리 플러그인
│   │   ├── recognition/         # OCR 및 템플릿 매칭 플러그인
├── settings/                    # 설정 관련 모듈
│   ├── __init__.py
│   ├── helpers.py               # 유틸리티 함수
│   ├── logger.py                # 로깅 시스템
│   ├── main.py                  # 실행 파일
├── utils/                       # 기타 유틸리티 기능
│   ├── __init__.py
│   ├── image_processing.py       # OpenCV 이미지 처리
│   ├── ocr_engine.py             # PaddleOCR 엔진
│   ├── file_manager.py           # 파일 관리
│   ├── json_validator.py         # JSON 검증
├── templates/                    # GUI 템플릿
│   ├── index.html                # 메인 UI
│   ├── settings.html             # 설정 UI
│   ├── logs.html                 # 로그 확인 페이지
├── static/                       # 정적 파일 (CSS, JS)
│   ├── css/style.css
│   ├── js/script.js
├── logs/                         # 실행 로그 저장
│   ├── system.log
│   ├── errors.log
├── README.md                     # 프로젝트 설명
├── requirements.txt               # 의존성 목록
└── manage.py                      # 실행 파일
