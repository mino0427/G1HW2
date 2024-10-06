import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 5000

cache_servers = []  # 캐시 서버 정보 저장 (IP, Port)

# 클라이언트 요청 처리 함수
def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")
    
    # 클라이언트에게 캐시 서버 정보를 전송
    for cache_server in cache_servers:
        conn.sendall(f"{cache_server[0]}:{cache_server[1]}\n".encode())
    conn.close()

# 캐시 서버 연결 처리 함수
def handle_cache_server(conn, addr):
    port = conn.recv(1024).decode()  # 캐시 서버의 포트 번호를 받음
    cache_servers.append((addr[0], port))  # 캐시 서버 정보 저장
    print(f"연결된 캐시 서버: {addr[0]}:{port}")
    conn.close()

def handle_request_from_cache_or_client(conn, addr):
    print(f"연결된 요청: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            
            # 파일 전송 처리
            file_size = file_num * 1024  # 파일 크기를 KB에서 Bytes로 변환
            response = f"{file_num}번 파일 전송 중"
            
            # 전송 속도: 1 Mbps = 125,000 Bps
            transfer_time = file_size / 125_000  # 전송 시간 계산
            time.sleep(transfer_time)
            
            conn.sendall(response.encode())
        except ConnectionResetError:
            print(f"{addr}와의 연결이 종료되었습니다.")
            break
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
