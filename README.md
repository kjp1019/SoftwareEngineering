# TOEIC 단어 학습 웹 애플리케이션

## 프로젝트 소개
이 프로젝트는 TOEIC 단어 학습을 위한 웹 애플리케이션입니다. 사용자들은 단어를 학습하고, 북마크하고, 개인 단어장을 만들 수 있습니다.

## 기술 스택
- Django 4.2(Python 3.8+)
- MySQL 8.0
- Bootstrap 5
- JavaScript

## 프로젝트 설정 및 실행 방법

### 1. 프로젝트 클론
```bash
git clone https://github.com/kjp1019/SoftwareEngineering.git
cd SoftwareEngineering
```

### 2. 가상환경 설정

#### Windows (PowerShell)
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
cd venv/scripts
.\activate.ps1
cd ..
cd ..
```

#### Windows (CMD)
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
cd venv/scripts
activate.bat
cd ..
cd ..
```

#### macOS/Linux
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 데이터베이스 설정
1. MySQL Workbench에서 데이터베이스 생성 및 덤프 파일 임포트
2. `import_words.py` 파일의 9번째 줄에서 데이터베이스 비밀번호를 본인의 MySQL 비밀번호로 수정

### 5. 데이터베이스 마이그레이션
```bash
python manage.py migrate
```

### 6. 서버 실행
```bash
python manage.py runserver
```

## 주의사항
- 프로젝트를 처음 실행할 때는 반드시 데이터베이스 테이블을 모두 삭제(DROP)한 후 마이그레이션을 진행해야 합니다.
- 새로운 계정을 생성하여 테스트하는 것을 권장합니다.

## 주요 기능
- 단어 학습
- 북마크
- 개인 단어장
- 학습 통계
- 데일리 미션

## 주요 기능

### 1. 단어장 관리
- 400개의 TOEIC 단어 데이터베이스
  - 초급 단어: 115개
  - 중급 단어: 146개
  - 고급 단어: 139개
- 난이도별 필터링
  - 초급: 초록색 배지로 표시
  - 중급: 노란색 배지로 표시
  - 고급: 빨간색 배지로 표시
- 단어 검색 기능
  - 영단어 검색
  - 한글 의미 검색
  - 실시간 검색 결과 표시
- 단어 발음 듣기 기능
  - Web Speech API를 활용한 발음 재생
  - 영국식/미국식 발음 지원
- 예문과 함께 단어 학습
  - 영문 예문 제공
  - 한글 번역 제공
  - 문맥을 통한 자연스러운 학습

### 2. 북마크 기능
- 단어 즐겨찾기
  - 별표 아이콘으로 북마크 표시
  - 클릭 한 번으로 북마크 토글
  - 실시간 북마크 상태 업데이트
- 북마크한 단어 모아보기
  - 북마크한 단어만 필터링
  - 북마크 순서대로 정렬
  - 북마크 수 표시
- 북마크 상태 실시간 업데이트
  - AJAX를 통한 비동기 처리
  - 페이지 새로고침 없이 상태 변경
  - 시각적 피드백 제공

### 3. 개인 단어장
- 개인별 단어장 관리
  - 폴더 아이콘으로 개인 단어장 표시
  - 클릭 한 번으로 단어 추가/제거
  - 실시간 상태 업데이트
- 단어 추가/제거 기능
  - 드래그 앤 드롭으로 단어 추가
  - 체크박스로 다중 선택
  - 일괄 추가/제거 기능
- 개인 단어장 상태 실시간 업데이트
  - AJAX를 통한 비동기 처리
  - 페이지 새로고침 없이 상태 변경
  - 시각적 피드백 제공

### 4. 관리자 기능
- 단어 추가/수정/삭제
  - 단일 단어 추가/수정
  - CSV 파일을 통한 일괄 추가
  - 단어 삭제 및 복구
- 단어 데이터 일괄 관리
  - 난이도별 단어 수정
  - 예문 일괄 업데이트
  - 데이터 백업 및 복원
- 사용자 관리
  - 사용자 권한 설정
  - 학습 현황 모니터링
  - 사용자 데이터 관리

## 기술 스택

### Backend
- Django 5.0.2
  - Django REST framework
  - Django ORM
  - Django Templates
  - Django Admin

### Frontend
- Bootstrap 5
  - 반응형 디자인
  - 그리드 시스템
  - 컴포넌트 라이브러리
- Font Awesome
  - 아이콘 라이브러리
  - 다양한 아이콘 제공
- JavaScript
  - Web Speech API
  - AJAX 통신
  - DOM 조작

### Database
- MySQL
  - InnoDB 엔진
  - UTF-8 인코딩
  - 인덱싱 최적화

## 설치 및 실행

1. 저장소 클론
```bash
git clone [repository-url]
cd sw_wordtest
```

2. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 의존성 설치
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# requirements.txt 설치
pip install -r requirements.txt
```

4. 데이터베이스 설정
```bash
# MySQL 접속
mysql -u root -p

# 데이터베이스 생성
CREATE DATABASE sw_wordtest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 사용자 생성 및 권한 부여
CREATE USER 'sw_wordtest_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sw_wordtest.* TO 'sw_wordtest_user'@'localhost';
FLUSH PRIVILEGES;
```

5. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 수정
# 데이터베이스 설정
DB_NAME=sw_wordtest
DB_USER=sw_wordtest_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# Django 설정
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

6. 데이터베이스 마이그레이션
```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

7. 서버 실행
```bash
# 개발 서버 실행
python manage.py runserver

# 프로덕션 서버 실행 (Gunicorn 사용 시)
gunicorn sw_wordtest.wsgi:application
```

## 프로젝트 구조

```
sw_wordtest/
├── apps/
│   ├── accounts/          # 사용자 관리
│   │   ├── models.py      # 사용자 모델
│   │   ├── views.py       # 사용자 관련 뷰
│   │   ├── urls.py        # URL 라우팅
│   │   └── templates/     # 사용자 관련 템플릿
│   └── vocabulary/        # 단어 관리
│       ├── models.py      # 단어 모델
│       ├── views.py       # 단어 관련 뷰
│       ├── urls.py        # URL 라우팅
│       └── templates/     # 단어 관련 템플릿
├── templates/             # 공통 템플릿
│   ├── base.html         # 기본 레이아웃
│   └── components/       # 재사용 컴포넌트
├── static/               # 정적 파일
│   ├── css/             # 스타일시트
│   ├── js/              # 자바스크립트
│   └── images/          # 이미지
├── media/               # 업로드 파일
├── requirements.txt     # 의존성 목록
├── manage.py           # Django 관리 스크립트
└── sw_wordtest/        # 프로젝트 설정
    ├── settings.py     # 프로젝트 설정
    ├── urls.py         # 메인 URL 설정
    └── wsgi.py         # WSGI 설정
```

## 데이터베이스 구조

### VocabularyWord
- id: 단어 ID (자동 증가)
- english: 영단어 (VARCHAR, 최대 100자)
- korean: 한글 의미 (VARCHAR, 최대 200자)
- part_of_speech: 품사 (VARCHAR, 최대 20자)
- difficulty: 난이도 (ENUM: 'easy', 'medium', 'hard')
- example_sentence: 예문 (TEXT)
- example_translation: 예문 번역 (TEXT)
- is_bookmarked: 북마크 여부 (BOOLEAN, 기본값: False)
- created_at: 생성일 (DATETIME, 자동 설정)
- updated_at: 수정일 (DATETIME, 자동 업데이트)

### 인덱스
- english: 영단어 검색 최적화
- difficulty: 난이도 필터링 최적화
- is_bookmarked: 북마크 필터링 최적화

## 단어 데이터 현황

### 전체 단어 수: 400개
- 초급: 115개 (28.75%)
- 중급: 146개 (36.5%)
- 고급: 139개 (34.75%)

### 품사별 분포
- 명사: 약 40%
- 동사: 약 30%
- 형용사: 약 20%
- 기타: 약 10%
