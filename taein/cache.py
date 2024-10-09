import socket
import threading
import time

# 고유 포트는 운영체제에서 자동으로 할당받음
HOST = '0.0.0.0'
DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000

# 전송 속도 설정 (초당 전송되는 kb 수)
CACHE_TO_CLIENT_SPEED = 3000
DATA_TO_CACHE_SPEED = 2000 

cache = {}

# 파일 전송 시간 계산 및 전송 처리
def send_file(conn, file_data, file_size_kb, speed_kbps):
    transfer_time = file_size_kb * 8 / speed_kbps  # 전송에 필요한 시간 계산
    print(f"전송 시간: {transfer_time:.2f}초 (파일 크기: {file_size_kb} KB, 속도: {speed_kbps} KB/s)")
    time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 실제 파일 데이터 전송
    total_bytes = len(file_data)
    sent_bytes = 0
    while sent_bytes < total_bytes:
        chunk_size = min(4096, total_bytes - sent_bytes)
        chunk = file_data[sent_bytes:sent_bytes + chunk_size]
        conn.sendall(chunk)
        sent_bytes += chunk_size

    conn.sendall(f"파일 전송 완료: {file_size_kb} kb".encode())

# 데이터 서버에서 파일을 요청하는 함수
def request_from_data_server(file_num):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
            s.sendall(str(file_num).encode())

            # 파일 크기 수신
            data = s.recv(1024).decode()
            file_size_kb = int(data)  # [수정됨]
            print(f"데이터 서버로부터 파일 크기 수신: {file_size_kb} kb")

            transfer_time = file_size_kb / DATA_TO_CACHE_SPEED
            print(f"데이터 서버에서 파일 수신 시작: 크기 {file_size_kb} kb, 예상 소요 시간 {transfer_time:.2f}초")
            time.sleep(transfer_time)
            print(f"데이터 서버에서 파일 수신 완료: 크기 {file_size_kb} kb, 실제 소요 시간 {transfer_time:.2f}초")

            # 실제 데이터 수신
            file_data = b''  # 파일 데이터를 저장할 바이트 문자열
            remaining_data = file_size_kb * 1024 // 8  # kb를 바이트로 변환
            while remaining_data > 0:
                chunk_size = min(4096, remaining_data)
                chunk = s.recv(chunk_size)
                if not chunk:
                    break
                file_data += chunk
                remaining_data -= len(chunk)

            print(f"데이터 서버에서 파일 수신 완료: 크기 {file_size_kb} kb, 실제 소요 시간 {transfer_time:.2f}초")

            with cache_lock:
                cache[file_num] = (file_data, file_size_kb)  # 파일 데이터와 크기를 저장
            # data = s.recv(1024)
            # return data.decode()
            return file_size_kb
        except Exception as e:
            print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")
            return None
        s.close()

def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            print(f"캐시 서버: {addr}로부터 {file_num}번 파일 요청 수신")

            # 캐시에 있는지 확인
            with cache_lock:
                if file_num in cache:
                    #캐시 히트
                    conn.sendall("Cache Hit".encode())
                    file_data, file_size_kb = cache[file_num]
                    file_size_kb = cache[file_num]  # [수정됨]
                    send_file(conn, file_data, file_size_kb, CACHE_TO_CLIENT_SPEED)
                    print(f"Cache Hit: {file_num}번 파일 캐시에서 {CACHE_TO_CLIENT_SPEED}로 전송")
                else:
                    # 캐시 미스
                    conn.sendall("Cache Miss".encode())
                    print(f"Cache Miss: {file_num}번 파일 캐시에 없음, 데이터 서버로 요청")
                    # 데이터 서버에서 파일을 가져옴
                    file_size_kb = request_from_data_server(file_num)
                    if file_size_kb is not None:
                        # 캐시에 파일 크기 저장
                        with cache_lock:
                            # cache[file_num] = file_size_kb
                            file_data, _ = cache[file_num]  # 방금 저장된 파일 데이터 가져옴

                        # 클라이언트에게 파일 크기 전송
                        conn.sendall(str(file_size_kb).encode())

                        # 파일 데이터 전송
                        send_file(conn, file_data, file_size_kb, CACHE_TO_CLIENT_SPEED)
                    else:
                        # 데이터 서버에서 파일을 가져오지 못한 경우
                        conn.sendall("File Not Found".encode())
        except ConnectionResetError:
            print(f"{addr}와의 연결이 종료되었습니다.")
            break
        except Exception as e:
            print(f"예외 발생: {e}")
            break
    conn.close()

def start_cache_server():
    global cache_lock
    cache_lock = threading.Lock()

    # 먼저 데이터 서버와 연결
    data_server_conn =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결 시도 중...")
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        print("데이터 서버 연결 완료!")

        # 캐시 서버 소켓 설정 (자동 포트 할당)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, 0))  # 운영체제가 자동으로 사용 가능한 포트 할당
        cache_port = server.getsockname()[1]  # 할당받은 포트 번호 확인
        print(f"캐시 서버의 할당된 포트 번호: {cache_port}")
        
        # 데이터 서버에 캐시 서버의 포트 번호 전송
        data_server_conn.sendall(str(cache_port).encode())
    except ConnectionRefusedError:
        print("데이터 서버에 연결할 수 없습니다. 데이터 서버가 실행 중인지 확인하세요.")
        return
    except Exception as e:
        print(f"데이터 서버 연결 중 예외 발생: {e}")
        return
        
    # 캐시 서버 실행
    server.listen()
    print(f"Cache Server가 {HOST}:{cache_port}에서 실행 중입니다...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_cache_server()
