import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 5000

# 전송 속도 설정 (초당 전송되는 KB 수)
DATA_TO_CLIENT_SPEED = 125  # 1 Mbps = 125 KB/s
DATA_TO_CACHE_SPEED = 250   # 2 Mbps = 250 KB/s

cache_servers = []  # 캐시 서버 정보 저장 (IP, Port)

# 파일 전송 시간 계산 및 전송 처리 함수
def send_file(conn, file_size, speed):
    transfer_time = file_size / speed  # 전송에 필요한 시간 계산
    print(f"전송 시간: {transfer_time}초 (파일 크기: {file_size} KB, 속도: {speed} KB/s)")
    time.sleep(transfer_time)  # 전송 시간 동안 대기
    conn.sendall(f"파일 전송 완료: {file_size} KB".encode())

# 클라이언트 요청 처리 함수
def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")
    
    # 클라이언트에게 캐시 서버 정보를 전송
    for cache_server in cache_servers:
        conn.sendall(f"{cache_server[0]}:{cache_server[1]}\n".encode())
    
    # 클라이언트로부터 파일 요청 처리
    while True:
        data = conn.recv(1024)
        if not data:
            break
        file_num = int(data.decode())
        file_size = file_num  # n번 파일은 n KB의 크기
        send_file(conn, file_size, DATA_TO_CLIENT_SPEED)
    
    conn.close()

# 캐시 서버 연결 처리 함수
def handle_cache_server(conn, addr):
    print(f"연결된 캐시 서버: {addr}")
    port = conn.recv(1024).decode()  # 캐시 서버의 포트 번호를 받음
    cache_servers.append((addr[0], port))  # 캐시 서버 정보 저장

    # 캐시 서버에서 파일 요청을 처리 (예시로 100번 파일 전송)
    file_num = 100  # 예를 들어, 100번 파일
    file_size = file_num  # 파일 크기는 파일 번호와 동일하게 가정 (100 KB)
    
    send_file(conn, file_size, DATA_TO_CACHE_SPEED)  # 캐시 서버에 파일 전송
    conn.close()

# 메인 서버 실행
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")
    
    # 먼저 캐시 서버와 연결
    for i in range(2):
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_cache_server, args=(conn, addr))
        thread.start()

    # 이후 클라이언트와 연결
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
