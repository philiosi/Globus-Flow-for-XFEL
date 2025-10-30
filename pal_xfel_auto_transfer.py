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
