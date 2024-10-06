import socket
import threading
import time

# 고유 포트는 운영체제에서 자동으로 할당받음
HOST = '0.0.0.0'
DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000

# 전송 속도 설정 (초당 전송되는 KB 수)
CACHE_TO_CLIENT_SPEED = 375  # 3 Mbps = 375 KB/s
DATA_TO_CACHE_SPEED = 250    # 2 Mbps = 250 KB/s

cache = {}

# 파일 전송 시간 계산 및 전송 처리
def send_file(conn, file_size, speed):
    transfer_time = file_size / speed  # 전송에 필요한 시간 계산
    print(f"전송 시간: {transfer_time}초 (파일 크기: {file_size} KB, 속도: {speed} KB/s)")
    time.sleep(transfer_time)  # 전송 시간 동안 대기
    conn.sendall(f"파일 전송 완료: {file_size} KB".encode())

# 데이터 서버에서 파일을 요청하는 함수
def request_from_data_server(file_num):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        s.sendall(str(file_num).encode())
        data = s.recv(1024)
        return data.decode()

# 클라이언트 요청 처리
def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            
            # 캐시에 있는지 확인
            if file_num in cache:
                print(f"Cache Hit: {file_num}번 파일")
                send_file(conn, file_num, CACHE_TO_CLIENT_SPEED)  # 캐시에서 클라이언트로 전송
            else:
                print(f"Cache Miss: {file_num}번 파일")
                # 데이터 서버에 파일 요청
                file_data = request_from_data_server(file_num)
                cache[file_num] = file_num  # 캐시에 저장
                send_file(conn, file_num, CACHE_TO_CLIENT_SPEED)  # 데이터 서버에서 받아온 파일을 클라이언트로 전송
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
