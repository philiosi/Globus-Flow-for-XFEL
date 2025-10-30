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
