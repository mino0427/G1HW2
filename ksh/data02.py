import socket
import threading
import time
import json

HOST = '0.0.0.0'
PORT = 5000
MAX_FILES = 10000  # 1부터 10000까지의 가상 파일 생성
MAX_CLIENTS = 4  # 클라이언트 4개 대기

# 전송 속도 설정 (초당 전송되는 KB 수)
DATA_TO_CLIENT_SPEED = 125  # 1 Mbps = 125 KB/s
DATA_TO_CACHE_SPEED = 250   # 2 Mbps = 250 KB/s

cache_servers = []  # 캐시 서버 정보 저장 (IP, Port)
virtual_files = {}  # 가상 파일 저장 (파일 번호: 파일 크기)

# 가상 파일 생성 (파일 크기만 저장)
def create_virtual_files():
    print("가상 파일 생성 시작...")
    for file_num in range(1, MAX_FILES + 1):
        file_size = (file_num % 10000) + 1  # 파일 크기는 1 ~ 10,000KB 반복
        virtual_files[file_num] = file_size  # 가상 데이터 대신 파일 크기만 저장
    print(f"총 {len(virtual_files)}개의 가상 파일 크기 정보 생성 완료!")

# 파일 전송 시간 계산 및 전송 처리 함수
def send_file(conn, file_size, speed):
    transfer_time = file_size / speed  # 전송에 필요한 시간 계산
    print(f"파일 전송 시간 계산: {transfer_time}초 (파일 크기: {file_size} KB, 속도: {speed} KB/s)")
    time.sleep(transfer_time)  # 전송 시간 동안 대기
    conn.sendall(f"파일 전송 완료: {file_size} KB".encode())
    print(f"파일 전송 완료 (크기: {file_size}KB)")

def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}로부터 파일 요청 처리 시작")

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print(f"클라이언트 {addr}로부터 데이터 수신 실패 또는 연결 종료")
                break

            # 클라이언트로부터 파일 요청 수신
            file_num = int(data.decode())
            print(f"데이터 서버: 클라이언트 {addr}로부터 {file_num}번 파일 요청 수신")

            # 요청한 파일을 가상 파일에서 찾음
            if file_num in virtual_files:
                file_size = virtual_files[file_num]
                print(f"데이터 서버: {file_num}번 파일 전송 준비 (크기: {file_size}KB)")
                send_file(conn, file_size, DATA_TO_CLIENT_SPEED)  # 클라이언트에게 파일 전송
            else:
                print(f"데이터 서버: {file_num}번 파일이 존재하지 않음")
                conn.sendall(f"파일 {file_num}번을 찾을 수 없습니다".encode())
        except ConnectionResetError:
            print(f"클라이언트 {addr}와의 연결이 끊어졌습니다.")
            break
        except Exception as e:
            print(f"예외 발생: {e}")
            break

    conn.close()
    print(f"클라이언트 {addr} 연결 종료")

# 캐시 서버 연결 처리 함수
def handle_cache_server(conn, addr):
    print(f"연결된 캐시 서버: {addr}")
    port = conn.recv(1024).decode()  # 캐시 서버의 포트 번호를 받음
    cache_servers.append((addr[0], port))  # 캐시 서버 정보 저장
    conn.close()

def start_server():
    file_creation_thread = threading.Thread(target=create_virtual_files)
    file_creation_thread.start()  # 가상 파일 생성 시작
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")

    # 캐시 서버 2개와 연결
    for i in range(2):
        conn, addr = server.accept()
        print(f"캐시 서버 {i + 1} 연결 완료: {addr}")
        thread = threading.Thread(target=handle_cache_server, args=(conn, addr))
        thread.start()

    # 클라이언트 연결 대기
    client_conns = []
    while len(client_conns) < MAX_CLIENTS:
        conn, addr = server.accept()
        client_conns.append((conn, addr))
        print(f"클라이언트 연결 완료: {addr}")

    for conn, addr in client_conns:
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

    file_creation_thread.join()  # 가상 파일 생성 완료까지 대기

if __name__ == "__main__":
    start_server()
