import socket
import json

DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000
MAX_FILES = 1000

virtual_storage = {}

def request_file_from_cache(cache_host, cache_port, file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cache_conn:
        print(f"클라이언트: 캐시 서버 {cache_host}:{cache_port}에 {file_num}번 파일 요청 중...")
        cache_conn.connect((cache_host, int(cache_port)))
        cache_conn.sendall(str(file_num).encode())

        # 파일 수신 처리
        data = cache_conn.recv(1024)
        response = data.decode()
        print(f"캐시 서버 응답: {response}")  # 캐시 서버에서 받은 응답 출력

        # 파일 수신 완료 확인
        if "파일 전송 완료" in response:
            virtual_storage[file_num] = response  # 가상 저장소에 저장
            print(f"파일 {file_num}번 캐시 서버로부터 수신 완료!")  # 파일 수신 완료 로그
            return "Cache Hit"
        else:
            return response

def request_file_from_data_server(file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        print(f"클라이언트: 데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 {file_num}번 파일 요청 중...")
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        data_server_conn.sendall(str(file_num).encode())

        # 파일 수신 처리
        data = data_server_conn.recv(1024)
        response = data.decode()
        print(f"데이터 서버 응답: {response}")  # 데이터 서버 응답 로그 출력

        # 파일 수신 완료 확인
        if "파일 전송 완료" in response:
            virtual_storage[file_num] = response  # 가상 저장소에 저장
            print(f"파일 {file_num}번 데이터 서버로부터 수신 완료!")  # 파일 수신 완료 로그

def request_file(file_num, cache_servers):
    print(f"파일 {file_num}번 요청 시작 (캐시 서버 우선)")
    for cache_host, cache_port in cache_servers:
        response = request_file_from_cache(cache_host, cache_port, file_num)
        if "Cache Hit" in response:
            print(f"파일 {file_num}번 캐시 서버에서 히트! 요청 종료")
            return

    print(f"파일 {file_num}번 캐시 미스 -> 데이터 서버에 요청 중...")
    request_file_from_data_server(file_num)

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}와 연결 완료!")

        # 캐시 서버 정보를 수신
        cache_servers = []
        while True:
            data = data_server_conn.recv(1024)
            if not data:
                break
            cache_servers.append(data.decode().strip().split(':'))
            print(f"수신한 캐시 서버 정보: {cache_servers[-1]}")  # 수신한 캐시 서버 정보 출력

    # 1,000개의 파일 요청 (예: 1번 ~ 1000번 파일을 요청)
    for file_num in range(1, MAX_FILES + 1):
        request_file(file_num, cache_servers)
        print(f"파일 {file_num}번 요청 완료")  # 각 파일 요청 완료 로그 출력

if __name__ == "__main__":
    start_client()
