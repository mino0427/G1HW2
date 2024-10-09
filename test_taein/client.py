import socket

DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000
MAX_FILES = 1000  # 클라이언트가 수신할 파일 개수

# 가상 파일 저장소
virtual_storage = {}  # 클라이언트가 받은 파일을 저장할 공간

# 캐시 서버에 파일 요청
def request_file_from_cache(cache_host, cache_port, file_num):
    cache_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"클라이언트: {cache_host}:{cache_port}로 {file_num}번 파일 요청 중...")
        cache_conn.connect((cache_host, int(cache_port)))
        cache_conn.sendall(str(file_num).encode())
        data = cache_conn.recv(1024)
        response = data.decode()

        # 캐시 히트/미스 여부 확인
        if "Cache Hit" in response:
            print(f"[{cache_host}:{cache_port}] 캐시 서버에서 캐시 히트: {file_num}번 파일 수신")
            return True  # 캐시 히트 발생
        elif "Cache Miss" in response:
            print(f"[{cache_host}:{cache_port}] 캐시 서버에서 캐시 미스: {file_num}번 파일 없음")
            return False  # 캐시 미스 발생
        else:
            print(f"알 수 없는 응답: {response}")
            return False
    finally:
        # 명시적으로 소켓 연결을 닫음
        cache_conn.close()

# 데이터 서버에 파일 요청
def request_file_from_data_server(file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        print(f"클라이언트: 데이터 서버로 {file_num}번 파일 요청 중...")
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        data_server_conn.sendall(str(file_num).encode())
        data = data_server_conn.recv(1024)
        print(f"데이터 서버에서 수신한 응답: {data.decode()}")
        virtual_storage[file_num] = data.decode()  # 가상 저장소에 파일 저장

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
