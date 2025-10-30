# Globus Flow 샘플 코드 - PAL-XFEL DAQ 시스템

PAL-XFEL DAQ 시스템에서 Globus Flow를 활용한 데이터 전송 자동화를 위한 샘플 코드 모음입니다.

## 파일 목록

### Python 스크립트
- `globus_auth.py` - Globus 인증 관리 모듈
- `run_transfer_flow.py` - 기본 Flow 실행 스크립트
- `watch_and_trigger.py` - 파일 감시 및 자동 트리거 스크립트
- `monitor_flow.py` - Flow 실행 상태 모니터링 스크립트
- `pal_xfel_auto_transfer.py` - PAL-XFEL 시스템 통합 스크립트

### 설정 파일
- `transfer_flow.json` - Flow 정의 파일
- `transfer_schema.json` - Flow 입력 스키마 파일
- `requirements.txt` - Python 패키지 의존성 목록

### 유틸리티
- `deploy_flow.sh` - Flow 배포 스크립트

## 빠른 시작

### 1. 환경 설정

```bash
# Python 가상환경 생성
python3 -m venv globus_flow_env
source globus_flow_env/bin/activate

# 패키지 설치
pip install -r requirements.txt

# Globus CLI 설치 (Flow 배포용)
pip install globus-cli
```

### 2. Globus App 등록

1. https://app.globus.org/settings/developers 접속
2. "Register a thick client or script that will be installed and run by users" 선택
3. Native App 생성
4. Client ID를 `globus_auth.py`의 `CLIENT_ID` 변수에 설정

```python
# globus_auth.py 수정
CLIENT_ID = "YOUR_CLIENT_ID_HERE"  # 여기에 발급받은 Client ID 입력
```

### 3. Flow 배포

```bash
# 실행 권한 부여
chmod +x deploy_flow.sh

# Flow 생성
./deploy_flow.sh

# 생성된 Flow ID 확인
cat flow_info.json
```

## 사용 예제

### 단일 전송 실행

```bash
python run_transfer_flow.py \
    --flow-id <FLOW_ID> \
    --source-collection <SOURCE_UUID> \
    --source-path /~/dat/ue_251023_FXL/rawData/scan001 \
    --dest-collection <DEST_UUID> \
    --dest-path /backup/ue_251023_FXL/rawData/scan001
```

### 자동 감시 및 전송

```bash
python watch_and_trigger.py \
    --watchdir /xfel/ffs/dat/ue_251023_FXL/rawData \
    --flow-id <FLOW_ID> \
    --source-collection <SOURCE_UUID> \
    --dest-collection <DEST_UUID> \
    --dest-base-path /backup \
    --patterns .done .complete
```

### Flow 실행 모니터링

```bash
python monitor_flow.py --run-id <RUN_ID>
```

### PAL-XFEL 통합 사용

```bash
python pal_xfel_auto_transfer.py \
    --scan-dir /xfel/ffs/dat/ue_251023_FXL/rawData/251023_alignment_00001_DIR \
    --flow-id <FLOW_ID> \
    --source-collection <SOURCE_UUID> \
    --dest-collection <DEST_UUID> \
    --dest-base /backup
```

## 주요 기능

### 1. 기본 데이터 전송 (run_transfer_flow.py)
- Globus Flow를 통한 고속 데이터 전송
- checksum 기반 무결성 검증
- 전송 상태 실시간 추적

### 2. 자동 트리거 (watch_and_trigger.py)
- 파일 시스템 감시 (watchdog)
- 스캔 완료 파일 감지 (.done, .complete 등)
- 자동 Flow 실행

### 3. 실시간 모니터링 (monitor_flow.py)
- Flow 실행 상태 추적
- 성공/실패 알림
- 진행 상황 로깅

### 4. PAL-XFEL 통합 (pal_xfel_auto_transfer.py)
- PAL-XFEL 디렉토리 구조 인식
- 실험 폴더 자동 분류 (ue_*, ms_*)
- 스캔별 자동 백업

## CentOS 7 환경 설정

### Python 3.6+ 설치

```bash
# Python 3.8 설치 (SCL 저장소)
sudo yum install centos-release-scl
sudo yum install rh-python38
scl enable rh-python38 bash
```

### systemd 서비스 등록

```bash
# /etc/systemd/system/globus-auto-transfer.service 파일 생성
sudo nano /etc/systemd/system/globus-auto-transfer.service
```

서비스 파일 내용:
```ini
[Unit]
Description=Globus Auto Transfer Service for PAL-XFEL
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/scripts
ExecStart=/path/to/globus_flow_env/bin/python watch_and_trigger.py \
    --watchdir /xfel/ffs/dat/ue_251023_FXL/rawData \
    --flow-id YOUR_FLOW_ID \
    --source-collection YOUR_SOURCE_UUID \
    --dest-collection YOUR_DEST_UUID \
    --dest-base-path /backup
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable globus-auto-transfer
sudo systemctl start globus-auto-transfer
sudo systemctl status globus-auto-transfer
```

## Collection UUID 확인

### Globus CLI 사용
```bash
globus endpoint search "PAL-XFEL"
```

### 웹 인터페이스 사용
https://app.globus.org/file-manager

## 문제 해결

### 인증 오류
```bash
# 토큰 파일 삭제 후 재인증
rm ~/.globus-flows-tokens.json
python run_transfer_flow.py ...
```

### Flow 실행 실패
```bash
# 로그 확인
python monitor_flow.py --run-id <RUN_ID>

# Flow 정의 확인
globus flows show <FLOW_ID>
```

### 파일 감시 문제
```bash
# watchdog 로그 확인
python watch_and_trigger.py --watchdir /path/to/watch
```

## 디렉토리 구조 예시

```
/xfel/ffs/dat/
├── ue_251023_FXL/           # 실험 폴더
│   ├── dat/                 # 통합 데이터
│   ├── rawData/             # 원시 데이터
│   │   ├── 251023_alignment_00001_DIR/
│   │   │   ├── PulseInfo/
│   │   │   ├── ScanInfo/
│   │   │   ├── detector1/
│   │   │   └── diagnostic1/
│   │   └── ...
│   └── scratch/             # 임시 작업 폴더
└── ...
```

## 참고 자료

- Globus SDK 문서: https://globus-sdk-python.readthedocs.io/
- Globus Flows API: https://docs.globus.org/api/flows/
- GitHub 예제: https://github.com/globus/globus-flows-trigger-examples
- PAL-XFEL: https://pal.postech.ac.kr/

## 라이선스

이 샘플 코드는 교육 및 연구 목적으로 제공됩니다.

## 작성 정보

- 작성일: 2025-10-30
- 버전: 1.0
- 대상 시스템: PAL-XFEL DAQ (CentOS 7)
