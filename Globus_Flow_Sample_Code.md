# Globus Flow 샘플 코드 가이드

## 목차
- [개요](#개요)
- [1단계: 기본 환경 설정](#1단계-기본-환경-설정)
- [2단계: Flow 정의 파일 작성](#2단계-flow-정의-파일-작성)
- [3단계: Flow 실행 코드](#3단계-flow-실행-코드)
- [4단계: Flow 배포 및 관리](#4단계-flow-배포-및-관리)
- [5단계: PAL-XFEL 통합 예제](#5단계-pal-xfel-통합-예제)
- [사용 방법 요약](#사용-방법-요약)

---

## 개요

이 문서는 PAL-XFEL DAQ 시스템에서 Globus Flow를 활용한 데이터 전송 자동화를 위한 샘플 코드를 제공합니다.

**주요 기능:**
- 대용량 데이터 전송 자동화
- 스캔 완료 시 자동 트리거
- Flow 실행 상태 모니터링
- PAL-XFEL 시스템 통합

**참고 자료:**
- Globus SDK 문서: https://globus-sdk-python.readthedocs.io/
- Globus Flows API: https://docs.globus.org/api/flows/
- GitHub 예제: https://github.com/globus/globus-flows-trigger-examples

---

## 1단계: 기본 환경 설정

### 1.1 필수 패키지 설치

```bash
# Python 가상환경 생성
python3 -m venv globus_flow_env
source globus_flow_env/bin/activate

# 필수 패키지 설치
pip install globus-sdk globus-compute-sdk watchdog
```

### 1.2 인증 설정 코드

**파일명: `globus_auth.py`**

```python
#!/usr/bin/env python
"""
globus_auth.py - Globus 인증 관리
"""
import os
import globus_sdk
from globus_sdk.tokenstorage import SimpleJSONFileAdapter

# 토큰 저장 경로
TOKEN_FILE = os.path.expanduser("~/.globus-flows-tokens.json")
TOKEN_FILE_ADAPTER = SimpleJSONFileAdapter(TOKEN_FILE)

# Globus App 클라이언트 ID (본인의 App ID로 교체 필요)
# https://app.globus.org/settings/developers 에서 등록
CLIENT_ID = "YOUR_CLIENT_ID_HERE"

# Globus Flows 서비스 스코프
SERVICE_SCOPES = [
    globus_sdk.FlowsClient.scopes.manage_flows,
    globus_sdk.FlowsClient.scopes.run,
    globus_sdk.FlowsClient.scopes.run_status,
    globus_sdk.FlowsClient.scopes.run_manage,
    globus_sdk.FlowsClient.scopes.view_flows,
]
RESOURCE_SERVER = globus_sdk.FlowsClient.resource_server

NATIVE_CLIENT = globus_sdk.NativeAppAuthClient(CLIENT_ID)


def get_tokens(scopes=None):
    """Globus 로그인 플로우 실행"""
    NATIVE_CLIENT.oauth2_start_flow(requested_scopes=scopes, refresh_tokens=True)
    authorize_url = NATIVE_CLIENT.oauth2_get_authorize_url()
    print(f"다음 URL에서 로그인하세요:\n\n{authorize_url}\n")
    auth_code = input("인증 코드 입력: ").strip()
    tokens = NATIVE_CLIENT.oauth2_exchange_code_for_tokens(auth_code)
    return tokens


def get_authorizer(flow_id=None):
    """인증자(Authorizer) 생성"""
    if flow_id:
        scopes = globus_sdk.SpecificFlowClient(flow_id).scopes.user
        resource_server = flow_id
    else:
        scopes = SERVICE_SCOPES
        resource_server = RESOURCE_SERVER

    # 저장된 토큰 로드
    if TOKEN_FILE_ADAPTER.file_exists():
        tokens = TOKEN_FILE_ADAPTER.get_token_data(resource_server)
    else:
        tokens = None

    if tokens is None:
        # 로그인 및 토큰 저장
        response = get_tokens(scopes=scopes)
        TOKEN_FILE_ADAPTER.store(response)
        tokens = response.by_resource_server[resource_server]

    return globus_sdk.RefreshTokenAuthorizer(
        tokens["refresh_token"],
        NATIVE_CLIENT,
        access_token=tokens["access_token"],
        expires_at=tokens["expires_at_seconds"],
        on_refresh=TOKEN_FILE_ADAPTER.on_refresh,
    )


def create_flows_client(flow_id=None):
    """FlowsClient 또는 SpecificFlowClient 생성"""
    authorizer = get_authorizer(flow_id=flow_id)
    if flow_id:
        return globus_sdk.SpecificFlowClient(flow_id, authorizer=authorizer)
    else:
        return globus_sdk.FlowsClient(authorizer=authorizer)
```

---

## 2단계: Flow 정의 파일 작성

### 2.1 기본 전송 Flow

**파일명: `transfer_flow.json`**

```json
{
  "Comment": "PAL-XFEL 데이터 전송 Flow",
  "StartAt": "TransferData",
  "States": {
    "TransferData": {
      "Comment": "원시 데이터를 목적지로 전송",
      "Type": "Action",
      "ActionUrl": "https://actions.automate.globus.org/transfer/transfer",
      "Parameters": {
        "source_endpoint_id.$": "$.input.source.id",
        "destination_endpoint_id.$": "$.input.destination.id",
        "transfer_items": [
          {
            "source_path.$": "$.input.source.path",
            "destination_path.$": "$.input.destination.path",
            "recursive.$": "$.input.recursive_tx"
          }
        ],
        "label": "PAL-XFEL Data Transfer",
        "sync_level": "checksum"
      },
      "ResultPath": "$.TransferResult",
      "WaitTime": 300,
      "End": true
    }
  }
}
```

### 2.2 입력 스키마

**파일명: `transfer_schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PAL-XFEL Transfer Flow 입력",
  "type": "object",
  "required": ["input"],
  "properties": {
    "input": {
      "type": "object",
      "required": ["source", "destination"],
      "properties": {
        "source": {
          "type": "object",
          "title": "소스 컬렉션",
          "required": ["id", "path"],
          "properties": {
            "id": {
              "type": "string",
              "format": "uuid",
              "title": "소스 컬렉션 UUID"
            },
            "path": {
              "type": "string",
              "title": "소스 경로"
            }
          }
        },
        "destination": {
          "type": "object",
          "title": "목적지 컬렉션",
          "required": ["id", "path"],
          "properties": {
            "id": {
              "type": "string",
              "format": "uuid",
              "title": "목적지 컬렉션 UUID"
            },
            "path": {
              "type": "string",
              "title": "목적지 경로"
            }
          }
        },
        "recursive_tx": {
          "type": "boolean",
          "title": "재귀적 전송",
          "default": true
        }
      }
    }
  }
}
```

---

## 3단계: Flow 실행 코드

### 3.1 기본 Flow 실행

**파일명: `run_transfer_flow.py`**

```python
#!/usr/bin/env python
"""
run_transfer_flow.py - PAL-XFEL 데이터 전송 Flow 실행
"""
import argparse
from globus_auth import create_flows_client


def run_transfer_flow(flow_id, source_collection, source_path, 
                      dest_collection, dest_path, label=None):
    """
    데이터 전송 Flow 실행
    
    Args:
        flow_id: Flow UUID
        source_collection: 소스 컬렉션 UUID
        source_path: 소스 경로
        dest_collection: 목적지 컬렉션 UUID
        dest_path: 목적지 경로
        label: Flow 실행 레이블
    """
    # Flow 클라이언트 생성
    fc = create_flows_client(flow_id=flow_id)
    
    # Flow 입력 데이터
    flow_input = {
        "input": {
            "source": {
                "id": source_collection,
                "path": source_path,
            },
            "destination": {
                "id": dest_collection,
                "path": dest_path,
            },
            "recursive_tx": True,
        }
    }
    
    # Flow 실행
    if label is None:
        label = f"PAL-XFEL Transfer: {source_path}"
    
    flow_run_request = fc.run_flow(
        body=flow_input,
        label=label,
        tags=["PAL-XFEL", "DAQ", "Raw-Data"],
    )
    
    run_id = flow_run_request["run_id"]
    print(f"\n✓ Flow 실행 성공!")
    print(f"  Run ID: {run_id}")
    print(f"  모니터링: https://app.globus.org/runs/{run_id}")
    
    return run_id


def main():
    parser = argparse.ArgumentParser(
        description="PAL-XFEL 데이터 전송 Flow 실행"
    )
    parser.add_argument("--flow-id", required=True, help="Flow UUID")
    parser.add_argument("--source-collection", required=True, 
                       help="소스 컬렉션 UUID")
    parser.add_argument("--source-path", required=True, 
                       help="소스 경로")
    parser.add_argument("--dest-collection", required=True, 
                       help="목적지 컬렉션 UUID")
    parser.add_argument("--dest-path", required=True, 
                       help="목적지 경로")
    parser.add_argument("--label", help="Flow 실행 레이블")
    
    args = parser.parse_args()
    
    run_transfer_flow(
        flow_id=args.flow_id,
        source_collection=args.source_collection,
        source_path=args.source_path,
        dest_collection=args.dest_collection,
        dest_path=args.dest_path,
        label=args.label
    )


if __name__ == "__main__":
    main()
```

### 3.2 자동 트리거 코드 (파일 감시)

**파일명: `watch_and_trigger.py`**

```python
#!/usr/bin/env python
"""
watch_and_trigger.py - 파일 생성 감지 시 자동으로 Flow 실행
PAL-XFEL DAQ 시스템의 스캔 완료를 감지하여 자동 전송
"""
import os
import time
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from globus_auth import create_flows_client


class ScanCompletionHandler(FileSystemEventHandler):
    """스캔 완료 감지 핸들러"""
    
    def __init__(self, flow_id, source_collection, dest_collection, 
                 dest_base_path, patterns=None):
        self.flow_id = flow_id
        self.source_collection = source_collection
        self.dest_collection = dest_collection
        self.dest_base_path = dest_base_path
        self.patterns = patterns or []
        self.fc = create_flows_client(flow_id=flow_id)
        
    def on_created(self, event):
        """파일 생성 이벤트 처리"""
        if event.is_directory:
            return
            
        # 패턴 확인
        if self.patterns:
            if not any(event.src_path.endswith(p) for p in self.patterns):
                return
        
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 파일 감지: {event.src_path}")
        
        # 스캔 디렉토리 추출
        scan_dir = os.path.dirname(event.src_path)
        scan_name = os.path.basename(scan_dir)
        
        # Globus 경로 변환 (로컬 경로 → Globus 경로)
        # 예: /data/rawData/... → /~/rawData/...
        source_path = self._convert_to_globus_path(scan_dir)
        dest_path = os.path.join(self.dest_base_path, scan_name, "")
        dest_path = dest_path.replace("\\", "/")
        
        # Flow 실행
        flow_input = {
            "input": {
                "source": {
                    "id": self.source_collection,
                    "path": source_path,
                },
                "destination": {
                    "id": self.dest_collection,
                    "path": dest_path,
                },
                "recursive_tx": True,
            }
        }
        
        label = f"Auto Transfer: {scan_name}"
        
        try:
            flow_run = self.fc.run_flow(
                body=flow_input,
                label=label,
                tags=["PAL-XFEL", "Auto", "DAQ"],
            )
            
            run_id = flow_run["run_id"]
            print(f"  ✓ Flow 실행: {run_id}")
            print(f"  소스: {source_path}")
            print(f"  목적지: {dest_path}")
            print(f"  모니터링: https://app.globus.org/runs/{run_id}")
            
        except Exception as e:
            print(f"  ✗ Flow 실행 실패: {e}")
    
    def _convert_to_globus_path(self, local_path):
        """로컬 경로를 Globus 경로로 변환"""
        # PAL-XFEL 환경에 맞게 수정 필요
        # 예: /xfel/ffs/dat/... → /~/dat/...
        if local_path.startswith("/xfel/ffs/"):
            return local_path.replace("/xfel/ffs", "/~")
        return local_path


def main():
    parser = argparse.ArgumentParser(
        description="PAL-XFEL 스캔 완료 감지 및 자동 전송"
    )
    parser.add_argument("--watchdir", required=True,
                       help="감시할 디렉토리")
    parser.add_argument("--flow-id", required=True,
                       help="Flow UUID")
    parser.add_argument("--source-collection", required=True,
                       help="소스 컬렉션 UUID")
    parser.add_argument("--dest-collection", required=True,
                       help="목적지 컬렉션 UUID")
    parser.add_argument("--dest-base-path", required=True,
                       help="목적지 기본 경로")
    parser.add_argument("--patterns", nargs="*", default=[".done", ".complete"],
                       help="감지할 파일 패턴 (예: .done .complete)")
    
    args = parser.parse_args()
    
    # 핸들러 및 옵저버 설정
    event_handler = ScanCompletionHandler(
        flow_id=args.flow_id,
        source_collection=args.source_collection,
        dest_collection=args.dest_collection,
        dest_base_path=args.dest_base_path,
        patterns=args.patterns
    )
    
    observer = Observer()
    observer.schedule(event_handler, args.watchdir, recursive=True)
    observer.start()
    
    print(f"\n=== PAL-XFEL 자동 전송 시작 ===")
    print(f"감시 디렉토리: {args.watchdir}")
    print(f"감지 패턴: {args.patterns}")
    print(f"Flow ID: {args.flow_id}")
    print(f"대기 중...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n\n감시 중지")
    
    observer.join()


if __name__ == "__main__":
    main()
```

---

## 4단계: Flow 배포 및 관리

### 4.1 Flow 생성 스크립트

**파일명: `deploy_flow.sh`**

```bash
#!/bin/bash
# deploy_flow.sh - Flow 배포 스크립트

FLOW_TITLE="PAL-XFEL Data Transfer Flow"
DEFINITION_FILE="transfer_flow.json"
SCHEMA_FILE="transfer_schema.json"

echo "=== Globus Flow 배포 ==="
echo "제목: $FLOW_TITLE"
echo "정의 파일: $DEFINITION_FILE"
echo "스키마 파일: $SCHEMA_FILE"
echo ""

# Flow 생성
globus flows create "$FLOW_TITLE" "$DEFINITION_FILE" \
    --input-schema "$SCHEMA_FILE" \
    --format json > flow_info.json

# Flow ID 추출
FLOW_ID=$(jq -r '.id' flow_info.json)

echo "✓ Flow 생성 완료!"
echo "  Flow ID: $FLOW_ID"
echo "  정보 파일: flow_info.json"
echo ""
echo "다음 명령으로 Flow 정보 확인:"
echo "  globus flows show $FLOW_ID"
```

### 4.2 Flow 상태 모니터링

**파일명: `monitor_flow.py`**

```python
#!/usr/bin/env python
"""
monitor_flow.py - Flow 실행 상태 모니터링
"""
import argparse
import time
from globus_auth import create_flows_client


def monitor_run(run_id, flow_id=None, interval=5):
    """
    Flow 실행 상태 모니터링
    
    Args:
        run_id: Run UUID
        flow_id: Flow UUID (선택)
        interval: 체크 간격 (초)
    """
    fc = create_flows_client(flow_id=flow_id)
    
    print(f"\n=== Flow 실행 모니터링 ===")
    print(f"Run ID: {run_id}")
    print(f"체크 간격: {interval}초\n")
    
    previous_status = None
    
    while True:
        try:
            run_info = fc.get_run(run_id)
            status = run_info["status"]
            
            if status != previous_status:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] 상태: {status}")
                
                if "details" in run_info:
                    details = run_info["details"]
                    if "description" in details:
                        print(f"  설명: {details['description']}")
                
                previous_status = status
            
            # 종료 상태 체크
            if status in ["SUCCEEDED", "FAILED", "INACTIVE"]:
                print(f"\n✓ Flow 실행 완료: {status}")
                
                if status == "SUCCEEDED":
                    print("  성공!")
                elif status == "FAILED":
                    print("  실패!")
                    if "details" in run_info:
                        print(f"  오류: {run_info['details']}")
                
                break
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\n\n모니터링 중지")
            break
        except Exception as e:
            print(f"오류: {e}")
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Globus Flow 실행 모니터링"
    )
    parser.add_argument("--run-id", required=True, help="Run UUID")
    parser.add_argument("--flow-id", help="Flow UUID (선택)")
    parser.add_argument("--interval", type=int, default=5,
                       help="체크 간격 (초)")
    
    args = parser.parse_args()
    
    monitor_run(
        run_id=args.run_id,
        flow_id=args.flow_id,
        interval=args.interval
    )


if __name__ == "__main__":
    main()
```

---

## 5단계: PAL-XFEL 통합 예제

**파일명: `pal_xfel_auto_transfer.py`**

```python
#!/usr/bin/env python
"""
pal_xfel_auto_transfer.py - PAL-XFEL DAQ 시스템 통합 예제
스캔 완료 후 자동으로 백업 서버로 전송
"""
import os
import re
import argparse
from datetime import datetime
from globus_auth import create_flows_client


class PALXFELAutoTransfer:
    """PAL-XFEL 자동 전송 관리자"""
    
    def __init__(self, flow_id, source_collection, dest_collection):
        self.flow_id = flow_id
        self.source_collection = source_collection
        self.dest_collection = dest_collection
        self.fc = create_flows_client(flow_id=flow_id)
    
    def parse_scan_dir(self, scan_dir):
        """
        스캔 디렉토리 경로 파싱
        예: /xfel/ffs/dat/ue_251023_FXL/rawData/251023_alignment_00001_DIR
        """
        parts = scan_dir.split('/')
        
        # 실험 폴더 추출
        exp_folder = None
        for part in parts:
            if re.match(r'(ue|ms)_\d+_[A-Z]+', part):
                exp_folder = part
                break
        
        # 스캔 이름 추출
        scan_name = os.path.basename(scan_dir)
        
        return {
            'experiment': exp_folder,
            'scan_name': scan_name,
            'full_path': scan_dir
        }
    
    def transfer_scan_data(self, scan_dir, dest_base="/backup"):
        """
        스캔 데이터 전송
        
        Args:
            scan_dir: 스캔 디렉토리 경로
            dest_base: 목적지 기본 경로
        """
        scan_info = self.parse_scan_dir(scan_dir)
        
        # Globus 경로 변환
        source_path = scan_dir.replace("/xfel/ffs", "/~")
        if not source_path.endswith("/"):
            source_path += "/"
        
        # 목적지 경로 구성
        dest_path = os.path.join(
            dest_base,
            scan_info['experiment'],
            "rawData",
            scan_info['scan_name'],
            ""
        ).replace("\\", "/")
        
        # Flow 입력
        flow_input = {
            "input": {
                "source": {
                    "id": self.source_collection,
                    "path": source_path,
                },
                "destination": {
                    "id": self.dest_collection,
                    "path": dest_path,
                },
                "recursive_tx": True,
            }
        }
        
        # 레이블 생성
        label = f"PAL-XFEL Auto: {scan_info['experiment']}/{scan_info['scan_name']}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n{'='*60}")
        print(f"[{timestamp}] 스캔 데이터 전송 시작")
        print(f"{'='*60}")
        print(f"실험: {scan_info['experiment']}")
        print(f"스캔: {scan_info['scan_name']}")
        print(f"소스: {source_path}")
        print(f"목적지: {dest_path}")
        
        try:
            flow_run = self.fc.run_flow(
                body=flow_input,
                label=label,
                tags=["PAL-XFEL", "DAQ", "Auto-Backup", scan_info['experiment']],
            )
            
            run_id = flow_run["run_id"]
            print(f"\n✓ 전송 요청 성공!")
            print(f"  Run ID: {run_id}")
            print(f"  모니터링: https://app.globus.org/runs/{run_id}")
            
            return run_id
            
        except Exception as e:
            print(f"\n✗ 전송 요청 실패: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="PAL-XFEL 스캔 데이터 자동 전송"
    )
    parser.add_argument("--scan-dir", required=True,
                       help="스캔 디렉토리 경로")
    parser.add_argument("--flow-id", required=True,
                       help="Flow UUID")
    parser.add_argument("--source-collection", required=True,
                       help="소스 컬렉션 UUID")
    parser.add_argument("--dest-collection", required=True,
                       help="목적지 컬렉션 UUID")
    parser.add_argument("--dest-base", default="/backup",
                       help="목적지 기본 경로")
    
    args = parser.parse_args()
    
    manager = PALXFELAutoTransfer(
        flow_id=args.flow_id,
        source_collection=args.source_collection,
        dest_collection=args.dest_collection
    )
    
    manager.transfer_scan_data(
        scan_dir=args.scan_dir,
        dest_base=args.dest_base
    )


if __name__ == "__main__":
    main()
```

---

## 사용 방법 요약

### 초기 설정

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv globus_flow_env
source globus_flow_env/bin/activate

# 2. 패키지 설치
pip install globus-sdk globus-compute-sdk watchdog

# 3. Globus App 등록
# https://app.globus.org/settings/developers 에서 Native App 생성
# CLIENT_ID를 globus_auth.py에 설정
```

### Flow 배포

```bash
# Flow 생성 및 배포
bash deploy_flow.sh

# 생성된 flow_info.json에서 Flow ID 확인
cat flow_info.json | jq -r '.id'
```

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
# 스캔 완료 파일 감지 시 자동 전송
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
# 특정 Run 상태 모니터링
python monitor_flow.py \
    --run-id <RUN_ID> \
    --interval 5
```

### PAL-XFEL 통합 사용

```bash
# 특정 스캔 디렉토리 전송
python pal_xfel_auto_transfer.py \
    --scan-dir /xfel/ffs/dat/ue_251023_FXL/rawData/251023_alignment_00001_DIR \
    --flow-id <FLOW_ID> \
    --source-collection <SOURCE_UUID> \
    --dest-collection <DEST_UUID> \
    --dest-base /backup
```

---

## 추가 참고사항

### CentOS 7 환경에서의 주의사항

1. **Python 버전**: Python 3.6 이상 필요
   ```bash
   python3 --version
   # 3.6 미만이면 SCL 저장소 사용
   sudo yum install centos-release-scl
   sudo yum install rh-python38
   scl enable rh-python38 bash
   ```

2. **방화벽 설정**: Globus 통신을 위한 포트 개방 필요
   ```bash
   # 필요 시 관리자에게 문의
   ```

3. **systemd 서비스 등록**: 자동 감시 스크립트를 서비스로 등록
   ```bash
   # /etc/systemd/system/globus-auto-transfer.service 생성
   # 서비스 시작: sudo systemctl start globus-auto-transfer
   ```

### Collection UUID 확인 방법

```bash
# Globus CLI로 컬렉션 검색
globus collection search "PAL-XFEL" --format json

# 또는 웹 인터페이스 사용
# https://app.globus.org/file-manager
```

### 문제 해결

**인증 오류 발생 시:**
```bash
# 토큰 파일 삭제 후 재인증
rm ~/.globus-flows-tokens.json
python run_transfer_flow.py ...
```

**Flow 실행 실패 시:**
```bash
# 로그 확인
python monitor_flow.py --run-id <RUN_ID>

# Flow 정의 확인
globus flows show <FLOW_ID>
```

---

## 연락처 및 지원

- **Globus 문서**: https://docs.globus.org/
- **Globus SDK GitHub**: https://github.com/globus/globus-sdk-python
- **PAL-XFEL 담당자**: [내부 연락처]

---

**작성일**: 2025-10-30  
**버전**: 1.0  
**대상 시스템**: PAL-XFEL DAQ (CentOS 7)
