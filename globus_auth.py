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
