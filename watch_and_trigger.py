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
