import socket
import threading
import json
import logging

HOST = '0.0.0.0'
PORT = 6000  # 각 Cache Server마다 포트 다르게 설정 가능
DATA_SERVER_HOST = 'localhost'  # Data Server의 IP 주소 (같은 머신에서 테스트 시 localhost)
DATA_SERVER_PORT = 5000  # Data Server의 포트

# 전송 속도 설정
CACHE_TO_CLIENT_SPEED = 3  # 3KB/ms

# 저장 용량 제한 (200 MB)
MAX_CACHE_SIZE = 200 * 1024  # KB 단위

# 캐시 저장소 (파일 번호: 파일 크기 KB)
cache_storage = {}
current_cache_size = 0
cache_lock = threading.Lock()

# 캐시 히트/미스 카운트
cache_hits = 0
cache_misses = 0
cache_count_lock = threading.Lock()

# 로그 설정
logging.basicConfig(filename='cache_server.log', level=logging.INFO, format='%(message)s')

# System Clock 참조 (Data Server와 동기화)
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

# Data Server의 시스템 클록과 동기화 (간단히 여기서는 별도의 클록 사용)
system_clock = SystemClock()

def log_event(event):
    timestamp = system_clock.get_time()
    logging.info(f"{timestamp}ms - {event}")

def send_file(conn, file_num, file_size, speed):
    # 전송 시간 계산
    transmission_time = file_size / speed  # 밀리초 단위
    log_event(f"파일 전송 시작: {file_num}, 크기: {file_size}KB, 속도: {speed}KB/ms")
    system_clock.advance_time(transmission_time)
    log_event(f"파일 전송 완료: {file_num}")
    response = {"status": "파일 전송 완료", "file_num": file_num, "file_size_kb": file_size}
    conn.sendall(json.dumps(response).encode())

def fetch_file_from_data_server(file_num):
    global current_cache_size
    try:
        data_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        data_conn.sendall(str(file_num).encode())
        response_start = data_conn.recv(4096).decode()
        response_data_start = json.loads(response_start)
        if response_data_start.get("status") != "파일 전송 시작":
            log_event(f"Data Server 응답 오류: {response_start}")
            data_conn.close()
            return None
        file_size = response_data_start.get("file_size_kb")
        
        # 파일 전송 완료 메시지 수신 (시뮬레이션)
        response_complete = data_conn.recv(4096).decode()
        response_data_complete = json.loads(response_complete)
        if response_data_complete.get("status") == "파일 전송 완료":
            log_event(f"Data Server로부터 파일 수신 완료: {file_num}")
            data_conn.close()
            return file_size
        else:
            log_event(f"Data Server 응답 오류: {response_complete}")
            data_conn.close()
            return None
    except Exception as e:
        log_event(f"Data Server에서 파일 가져오기 오류: {e}")
        return None

def handle_client(conn, addr):
    global current_cache_size, cache_hits, cache_misses
    log_event(f"연결 시작: {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            file_num = int(data.decode())
            log_event(f"파일 요청: {file_num} from {addr}")

            with cache_lock:
                if file_num in cache_storage:
                    file_size = cache_storage[file_num]
                    with cache_count_lock:
                        cache_hits += 1
                    log_event(f"캐시 히트: {file_num}")
                    send_file(conn, file_num, file_size, CACHE_TO_CLIENT_SPEED)
                else:
                    with cache_count_lock:
                        cache_misses += 1
                    log_event(f"캐시 미스: {file_num}")
                    # Data Server에서 파일 가져오기
                    file_size = fetch_file_from_data_server(file_num)
                    if file_size:
                        if current_cache_size + file_size <= MAX_CACHE_SIZE:
                            cache_storage[file_num] = file_size
                            current_cache_size += file_size
                            log_event(f"파일 캐시에 저장: {file_num}, 현재 캐시 용량: {current_cache_size}KB")
                            send_file(conn, file_num, file_size, CACHE_TO_CLIENT_SPEED)
                        else:
                            log_event(f"캐시 용량 초과: {file_num}. 클라이언트에게 직접 Data Server 요청 지시.")
                            response = {"status": "캐시 용량 초과. Data Server로 직접 요청하세요."}
                            conn.sendall(json.dumps(response).encode())
                    else:
                        response = {"status": "파일을 가져오는 데 실패했습니다."}
                        conn.sendall(json.dumps(response).encode())
    except Exception as e:
        log_event(f"오류 발생: {e}")
    finally:
        conn.close()
        log_event(f"연결 종료: {addr}")

def start_cache_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    log_event(f"Cache Server 실행: {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start_cache_server()
