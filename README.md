Drovis_v3의 레포지토리입니다.

# Python Implementation of the Ethereum protocol

[![Join the conversation on Discord](https://img.shields.io/discord/809793915578089484?color=blue&label=chat&logo=discord&logoColor=white)](https://discord.gg/GHryRvPB84)
[![Build Status](https://circleci.com/gh/ethereum/py-evm.svg?style=shield)](https://circleci.com/gh/ethereum/py-evm)
[![PyPI version](https://badge.fury.io/py/py-evm.svg)](https://badge.fury.io/py/py-evm)
[![Python versions](https://img.shields.io/pypi/pyversions/py-evm.svg)](https://pypi.python.org/pypi/py-evm)
[![Docs build](https://readthedocs.org/projects/py-evm/badge/?version=latest)](https://py-evm.readthedocs.io/en/latest/?badge=latest)

## Drovis

Drovis was developed as a project for the 2025 Convergence Security Creative Software Competition.
This project aims to develop security software that identifies the behaviors of drug droppers in crime scenes by automatically analyzing video data.
Since traditional video analysis methods relying on manual review are limited by manpower and time, the system utilizes AI-based analysis technology to enable automated detection.

In South Korea, illegal drug distribution through private messengers such as Telegram has emerged as a serious problem, with drug-related cases accounting for 31.7% of all detected illegal online transactions.
Drug crimes are characterized by anonymity and speed, making them difficult to address using conventional manual surveillance systems.

### Goals

Drovis aims to develop security software that automatically detects drug mules using AI-based multimodal analysis technology.

In particular Drovis aims to:

- automatically analyze video data to reduce manpower and time consumption
- combine Pose Estimation with LSTM to precisely recognize behavioral patterns
- detect suspicious drug dropping behaviors such as loitering and hand-offs
- assess the likelihood of criminal activity (high / medium / low) through AI analysis
- implement a flexible model architecture suitable for research, experimentation, and further expansion
- complement the limitations of traditional manual surveillance systems and contribute to public safety


## Installation & Usage

### Windows 
```sh
python3.10 -m venv venv310
\venv310\Scripts\activate
git clone https://github.com/JJeongsuu/Drovis_v3.git
pip install -r requirements.txt
```

### Mac / Linux
```sh
python3.10 -m venv venv310
source venv310/bin/activate
git clone https://github.com/JJeongsuu/Drovis_v3.git
pip install -r requirements.txt
```

## 프로젝트 소개

### 개발배경 및 필요성

### 개발 목표 및 주요 내용

### 상세 설계
project-root/
├── app.py                        # 앱 실행 진입점 
│
├── core/                         # 백엔드 로직
│   ├── config.py                 # 환경 설정
│   ├── db.py                     # SQLite 연결 객체
│
│   ├── models/                   # DB 테이블 구조 정의
│   │   ├── __init__.py
│   │   ├── lstm_model.py         # 모델 정의
│   │   ├── user_DB.py            # 사용자 정보 테이블
│   │   └── analysis_DB.py        # 분석 결과 테이블
│
│   ├── services/                 # 주요 기능 로직
│   │   ├── __init__.py
│   │   ├── auth.py               # 로그인/회원가입 처리
│   │   ├── preprocess.py         # 영상 → npy 변환 
│   │   ├── predict.py            # 위의 npy 받아서 AI 모델 로딩 및 예측
│   │   ├── save_analysis.py      # 분석 결과 저장
│   │   └── history.py            # 분석 기록 조회
│
├── gui/                          # 프론트엔드 UI (PyQt5)
│   ├── login_window.py           # 로그인 창
│   ├── register_window.py        # 회원가입 창
│   ├── main_window.py            # 메인 메뉴 역할
│   ├── upload_window.py          # 파일 업로드, 로딩창
│   ├── history_window.py         # 분석 기록 조회 창
│   └── styles.qss                # 전역 스타일시트 
│
├── uploads/                      # 영상 저장될 위치
│   └── __init__.py
│
├── ai_models/                    # 학습시킨 AI 모델 저장소
│   ├── lstm_model.pt             # 학습시킨 AI 모델 (pytorch)
│   └── users.db                  # 
│
├── database/                     # SQLite DB 파일 저장 위치
│   ├── analysis.db               # 분석기록 DB
│   └── users.db                  # 사용자 DB
│
├── assets/                       
│   └── Drovis_logo.ico           # Drovis 로고
│
├── requirements.txt              
├── README.md                     
└── .gitignore                    


### 시연 영상


## TEAM : 두뇌풀가동

| 장은정 | 김민경 | 나정수 | 조효빈 | 
|:-------:|:-------:|:-------:|:-------:|
| 팀장 <br/> AI 개발 | 디자이너 <br/> 프론트엔드 개발 |<br/> 백엔드 개발 | <br/> 백엔드 개발 |

## Documentation

[Get started in 5 minutes](https://py-evm.readthedocs.io/en/latest/guides/building_an_app_that_uses_pyevm.html)

Check out the [documentation on our official website](https://py-evm.readthedocs.io/en/latest/)

View the [change log](https://py-evm.readthedocs.io/en/latest/release_notes.html).
