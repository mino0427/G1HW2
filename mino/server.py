import socket
import threading
import json
import logging

HOST = '0.0.0.0'
PORT = 5000

# System Clock (가상의 시스템 클록)
class SystemClock:
    def __init__(self):
        self.current_time = 0  # 밀리초 단위
        self.lock = threading.Lock()
    
    def advance_time(self, delta):
        with self.lock:
            self.current_time += delta
            return self.current_time
    
    def get_time(self):
        with self.lock:
            return self.current_time

system_clock = SystemClock()

# 로그 설정
logging.basicConfig(filename='data_server.log', level=logging.INFO, format='%(message)s')

# 가상 파일 생성 (파일 번호: 파일 크기 KB)
virtual_files = {i: i for i in range(1, 10001)}  # 1번 파일: 1KB, ..., 10000번 파일: 10000KB

def log_event(event):
    timestamp = system_clock.get_time()
    logging.info(f"{timestamp}ms - {event}")

def handle_request(conn, addr):
    log_event(f"연결 시작: {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            log_event(f"파일 요청: {file_num} from {addr}")
            file_size = virtual_files.get(file_num)
            if not file_size:
                response = {"status": "파일 없음"}
                conn.sendall(json.dumps(response).encode())
                log_event(f"파일 없음: {file_num}")
                continue

            # 파일 전송 시작
            response = {"status": "파일 전송 시작", "file_num": file_num, "file_size_kb": file_size}
            conn.sendall(json.dumps(response).encode())
            log_event(f"파일 전송 시작: {file_num}")

            # 전송 시간 계산 (Data Server ↔ Client: 1Mbps -> 1KB/ms)
            transmission_time = file_size  # 밀리초 단위
            system_clock.advance_time(transmission_time)
            log_event(f"파일 전송 완료: {file_num}")
            completion_message = {"status": "파일 전송 완료", "file_num": file_num, "file_size_kb": file_size}
            conn.sendall(json.dumps(completion_message).encode())
    except Exception as e:
        log_event(f"오류 발생: {e}")
    finally:
        conn.close()
        log_event(f"연결 종료: {addr}")

def start_data_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    log_event(f"Data Server 실행: {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_request, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start_data_server()
