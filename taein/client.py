import socket

DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000

# 캐시 서버에 연결하여 파일 요청
def request_file_from_cache(cache_host, cache_port, file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cache_conn:
        cache_conn.connect((cache_host, int(cache_port)))
        cache_conn.sendall(str(file_num).encode())
        data = cache_conn.recv(1024)
        # 캐시 서버 정보와 함께 수신한 데이터 출력
        print(f"[{cache_host}:{cache_port}] 캐시 서버에서 수신한 응답: {data.decode()}")

# 메인 클라이언트 함수
def start_client():
    # 데이터 서버에 연결
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        
        # 캐시 서버 정보를 수신
        cache_servers = []
        while True:
            data = data_server_conn.recv(1024)
            if not data:
                break
            cache_servers.append(data.decode().strip())

    # 받은 캐시 서버 정보 출력 및 파일 요청
    print(f"수신한 캐시 서버 정보: {cache_servers}")
    for i, cache_server in enumerate(cache_servers):
        cache_host, cache_port = cache_server.split(':')
        request_file_from_cache(cache_host, cache_port, i + 1)  # 예시: 1번 파일부터 순서대로 요청

if __name__ == "__main__":
    start_client()
