import socket
import threading

# 고유 포트는 운영체제에서 자동으로 할당받음
HOST = '0.0.0.0'
DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000

cache = {}

# 클라이언트 요청 처리
def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            # 캐시에서 파일 확인
            if file_num in cache:
                response = f"Cache Hit: {file_num}번 파일"
            else:
                response = f"Cache Miss: {file_num}번 파일"
            conn.sendall(response.encode())
        except ConnectionResetError:
            print(f"{addr}와의 연결이 종료되었습니다.")
            break
    conn.close()

# 메인 캐시 서버 실행
def start_cache_server():
    # 먼저 데이터 서버와 연결
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server_conn:
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        
        # 캐시 서버 소켓 설정
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, 0))  # 운영체제가 자동으로 사용 가능한 포트 할당
        cache_port = server.getsockname()[1]  # 할당받은 포트 번호 확인
        print(f"캐시 서버의 할당된 포트 번호: {cache_port}")
        
        # 데이터 서버에 캐시 서버의 포트 번호 전송
        data_server_conn.sendall(str(cache_port).encode())
        
        server.listen()
        print(f"Cache Server가 {HOST}:{cache_port}에서 실행 중입니다...")
        
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    start_cache_server()
