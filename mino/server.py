import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 5000
MAX_CLIENTS = 4  # 클라이언트 4개 대기

# 전송 속도 설정 (초당 전송되는 kb 수)
DATA_TO_CLIENT_SPEED = 1000  # kb단위로 가야함
DATA_TO_CACHE_SPEED = 2000

cache_servers = []  # 캐시 서버 정보 저장 (IP, Port)
virtual_files = {}  # 가상 파일 저장 (파일 번호: 파일 크기)

virtual_files_lock = threading.Lock()
# 가상 파일 생성
def create_virtual_files():
    print("가상 파일 생성 시작...")
    with virtual_files_lock:
        for file_num in range(1, 100001):
            file_size = (file_num % 10000) + 1  # 파일 크기는 1 ~ 10,000kb 반복
            virtual_files[file_num] = file_size  # 파일 크기만 저장 (kb 단위)
    print(f"총 {len(virtual_files)}개의 가상 파일 크기 정보 생성 완료!")


# 파일 전송 시간 계산 및 전송 처리 함수
def send_file(conn, file_num, file_size_kb, speed_kbps):
    # 파일 크기 전송
    conn.sendall(str(file_size_kb).encode())

    transfer_time = file_size_kb / speed_kbps  # 전송에 필요한 시간 계산
    print(f"파일 전송 시작: 파일 번호 {file_num}, 크기 {file_size_kb} kb, 예상 소요 시간 {transfer_time:.2f}초")
    time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 실제 파일 데이터 전송
    total_bytes = file_size_kb * 1024 // 8  # 바이트 단위로 변환
    file_data = b'X' * total_bytes  # 가상 데이터 생성
    conn.sendall(file_data)  # 전체 파일 데이터 전송
    print(f"파일 전송 완료: 파일 번호 {file_num}, 크기 {file_size_kb} kb, 실제 소요 시간 {transfer_time:.2f}초")

def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}로부터 파일 요청 처리 시작")
    
    # 클라이언트에게 캐시 서버 정보를 전송
    for cache_server in cache_servers:
        conn.sendall(f"{cache_server[0]}:{cache_server[1]}\n".encode())

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            print(f"데이터 서버: {addr}로부터 {file_num}번 파일 요청 수신")

            # 요청한 파일의 크기 계산
            file_size_kb = ((file_num - 1) % 10000) + 1  # 파일 크기: 1 ~ 10,000 kb
            send_file(conn, file_num, file_size_kb, DATA_TO_CACHE_SPEED)
            # file_num = int(data.decode())
        except ValueError:
            print(f"잘못된 파일 번호 수신: {data}")
            conn.sendall("잘못된 요청입니다.".encode())
            continue

        # 요청한 파일을 가상 파일에서 찾음
        with virtual_files_lock:
            if file_num in virtual_files:
                file_size = virtual_files[file_num]  # 파일 크기 (kb 단위) 파일 크기가 파일 번호인데
            else:
                print(f"데이터 서버: {file_num}번 파일을 찾을 수 없음")
                conn.sendall(f"파일을 찾을 수 없습니다: {file_num}".encode())
                continue

        send_file(conn, file_size, DATA_TO_CLIENT_SPEED)  # 클라이언트에게 파일 전송

    conn.close()


# 캐시 서버 연결 처리 함수
def handle_cache_server(conn, addr):
    print(f"연결된 캐시 서버: {addr}")
    port = conn.recv(1024).decode()  # 캐시 서버의 포트 번호를 받음
    cache_servers.append((addr[0], port))  # 캐시 서버 정보 저장

    # 캐시 서버에 대한 추가 처리 가능
    conn.close()

def start_server():
    # create_virtual_files()  # 서버가 시작되면 가상 파일 생성
    # 가상 파일 생성을 별도의 스레드로 실행
    file_creation_thread = threading.Thread(target=create_virtual_files)
    file_creation_thread.start()  # 가상 파일 생성 시작
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    # 데이터 서버 실행 중이라는 메시지 출력
    print(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")

    # 먼저 캐시 서버 2개와 연결
    print("캐시 서버와 연결 중...")
    for i in range(2):  # 캐시 서버 2개 연결
        conn, addr = server.accept()
        print(f"캐시 서버 {i + 1} 연결 완료: {addr}")
        thread = threading.Thread(target=handle_cache_server, args=(conn, addr))
        thread.start()

    # 캐시 서버와 연결 후 클라이언트와 연결
    print("클라이언트 연결 대기 중...")
    client_conns = []  # 클라이언트 연결 저장

    # 4개의 클라이언트가 모두 연결될 때까지 대기
    while len(client_conns) < MAX_CLIENTS:
        conn, addr = server.accept()
        client_conns.append((conn, addr))
        print(f"클라이언트 연결 완료: {addr}")

        # 클라이언트에게 캐시 서버 정보를 전송
        for cache_server in cache_servers:
            conn.sendall(f"{cache_server[0]}:{cache_server[1]}\n".encode())

    # 4개의 클라이언트가 연결된 후에 요청 처리 시작
    print(f"모든 클라이언트가 연결됨. 파일 전송 시작.")
    for conn, addr in client_conns:
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

    # 파일 생성이 완료될 때까지 기다림
    file_creation_thread.join()  # 이 줄은 파일 생성이 끝날 때까지 기다리게 함

if __name__ == "__main__":
    start_server()
