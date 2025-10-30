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
