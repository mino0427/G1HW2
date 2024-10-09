import socket
import time

DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000
MAX_FILES = 1000  # 클라이언트가 수신할 파일 개수

DOWNLOAD_SPEED_FROM_DATA_SERVER = 1000  # 데이터 서버에서 다운로드 속도 (1 Mbps = 1000 kb/s)
DOWNLOAD_SPEED_FROM_CACHE_SERVER = 3000  # 캐시 서버에서 다운로드 속도 (3 Mbps = 3000 kb/s)

# 가상 파일 저장소
virtual_storage = {}  # 클라이언트가 받은 파일을 저장할 공간

# 파일 데이터 수신 함수
def receive_file(conn, file_size_kb, donwload_speed_kbps):
    # 전송 시간 계산 및 시뮬레이션
    transfer_time = file_size_kb / donwload_speed_kbps  # 전송 시간 계산 (초 단위)
    print(f"파일 수신 시작: 크기 {file_size_kb} kb, 예상 소요 시간 {transfer_time:.2f}초")
    time.sleep(transfer_time)  # 전송 시간 시뮬레이션
    
    # 실제 데이터 수신
    file_data = b''  # 파일 데이터를 저장할 바이트 문자열
    remaining_data = file_size_kb * 1024 // 8  # kb를 바이트로 변환 (1kb = 1024비트, 1바이트 = 8비트)
    while remaining_data > 0:
        chunk = conn.recv(min(4096, remaining_data))
        if not chunk:
            break
        file_data += chunk
        remaining_data -= len(chunk)

    print(f"파일 수신 완료: 크기 {file_size_kb} kb, 실제 소요 시간 {transfer_time:.2f}초")
    
    # 수신한 데이터를 가상 저장소에 저장
    return file_data

# 캐시 서버에 파일 요청
def request_file_from_cache(cache_host, cache_port, file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cache_conn:
        try:
            print(f"클라이언트: {cache_host}:{cache_port}로 {file_num}번 파일 요청 중...")
            cache_conn.connect((cache_host, int(cache_port)))
            print(f"캐시 서버 {cache_host}:{cache_port}에 연결되었습니다.")
            cache_conn.sendall(str(file_num).encode())

            # 캐시 서버의 응답 수신
            response = cache_conn.recv(1024).decode()
            if response == "Cache Hit":
                print(f"캐시 히트 발생: {file_num}번 파일")

                #파일 크기 수신
                data = cache_conn.recv(1024).decode()
                file_size_kb = int(data)
                print(f"캐시 서버로부터 파일 크기 수신: {file_size_kb} kb")

                # 파일 데이터 수신
                file_data = receive_file(cache_conn, file_size_kb, DOWNLOAD_SPEED_FROM_CACHE_SERVER)
                virtual_storage[file_num] = file_data  # 가상 저장소에 파일 데이터 저장
                print(f"캐시 서버에서 파일 수신 완료: {file_num}번 파일")
                return True  # 파일 수신 성공
            elif response == "Cache Miss":
                print(f"캐시 미스 발생: {file_num}번 파일")
                return False  # 캐시 미스 발생
            else:
                print(f"알 수 없는 응답: {response}")
                return False  # 오류 처리
        
        except Exception as e:
            print(f"캐시 서버에서 파일 수신 중 오류 발생")
            return False  # 파일 수신 실패

# 데이터 서버에 파일 요청
def request_file_from_data_server(file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        try:
            print(f"데이터 서버로 {file_num}번 파일 요청 중...")
            data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
            print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결되었습니다.")
            data_server_conn.sendall(str(file_num).encode())
            
            # 파일 크기 수신
            data = data_server_conn.recv(1024).decode()
            file_size_kb = int(data)
            print(f"데이터 서버로부터 파일 크기 수신: {file_size_kb} kb")
            
            # 파일 데이터 수신
            file_data = receive_file(data_server_conn, file_size_kb, DOWNLOAD_SPEED_FROM_DATA_SERVER)
            virtual_storage[file_num] = file_data  # 가상 저장소에 파일 데이터 저장
            print(f"데이터 서버에서 파일 수신 완료: {file_num}번 파일")
        except Exception as e:
            print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")

# 파일 요청 로직 최적화
def request_file(file_num, cache_servers):
    # 캐시 서버 우선 요청
    for cache_host, cache_port in cache_servers:
        if request_file_from_cache(cache_host, cache_port, file_num):
            # 캐시 히트 시, 더 이상 데이터 서버에 요청하지 않음
            return

    # 모든 캐시 서버에서 캐시 미스가 발생하면 데이터 서버에 요청
    print(f"{file_num}번 파일 캐시 서버에서 캐시 미스 -> 데이터 서버로 요청")
    request_file_from_data_server(file_num)

# 메인 클라이언트 함수
def start_client():
    # 데이터 서버에 연결하여 캐시 서버 정보 수신
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        
        # 캐시 서버 정보를 수신
        cache_servers = []
        while True:
            data = data_server_conn.recv(1024)
            if not data:
                break
            cache_servers.append(data.decode().strip().split(':'))

    print(f"수신한 캐시 서버 정보: {cache_servers}")

    # 1,000개의 파일 요청 (예: 1번 ~ 1000번 파일을 요청)
    for file_num in range(1, MAX_FILES + 1):
        request_file(file_num, cache_servers)

if __name__ == "__main__":
    start_client()
