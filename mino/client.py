import socket
import threading
import json
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 설정
CACHE_SERVERS = [
    ('localhost', 6000),  # Cache Server 1
    ('localhost', 6001)   # Cache Server 2 (포트 6001로 설정)
]
DATA_SERVER = ('localhost', 5000)
TOTAL_FILES = 1000
FILE_RANGE = (1, 10000)
MAX_CONCURRENT_DOWNLOADS = 50  # 동시에 다운로드할 파일 수

# 로그 설정
logging.basicConfig(filename='client.log', level=logging.INFO, format='%(message)s')

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

system_clock = SystemClock()

def log_event(event):
    timestamp = system_clock.get_time()
    logging.info(f"{timestamp}ms - {event}")

# 파일 다운로드 결과 저장 (파일 순서: (파일 번호, 파일 크기))
download_results = {}
download_lock = threading.Lock()

def select_cache_server(index):
    return CACHE_SERVERS[index % len(CACHE_SERVERS)]

def send_request(server, file_num, speed):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(server)
            s.sendall(str(file_num).encode())
            response_start = s.recv(4096).decode()
            response_data_start = json.loads(response_start)
            if response_data_start.get("status") == "파일 전송 시작":
                # 전송 시간 계산
                file_size = response_data_start.get("file_size_kb")
                transmission_time = file_size / speed  # 밀리초 단위
                log_event(f"파일 전송 시작: {file_num} from {server}")
                system_clock.advance_time(transmission_time)
                log_event(f"파일 전송 완료: {file_num} from {server}")
                response_complete = s.recv(4096).decode()
                response_data_complete = json.loads(response_complete)
                if response_data_complete.get("status") == "파일 전송 완료":
                    return file_num, file_size
            elif response_data_start.get("status") == "캐시 용량 초과. Data Server로 직접 요청하세요.":
                log_event(f"캐시 용량 초과: {file_num}. Data Server로 직접 요청.")
                return None
            else:
                log_event(f"응답 오류: {file_num} from {server}")
                return None
    except Exception as e:
        log_event(f"서버 {server}에 요청 중 오류 발생: {e}")
        return None

def download_file(file_num, file_order, cache_server_index):
    # Cache Server 선택 (Round Robin)
    cache_server = select_cache_server(cache_server_index)
    result = send_request(cache_server, file_num, 3)  # Cache Server ↔ Client: 3KB/ms
    
    if result:
        return (file_order, file_num, result[1])
    else:
        # Cache Server에서 파일을 가져오지 못했을 경우 Data Server에서 다운로드
        result = send_request(DATA_SERVER, file_num, 1)  # Data Server ↔ Client: 1KB/ms
        if result:
            return (file_order, file_num, result[1])
        else:
            log_event(f"파일 다운로드 실패: {file_num}")
            return (file_order, file_num, None)

def main():
    global system_clock
    # 무작위로 1000개의 파일 선택
    selected_files = random.sample(range(FILE_RANGE[0], FILE_RANGE[1] + 1), TOTAL_FILES)
    # 파일 순서 유지
    file_order_mapping = {i: file_num for i, file_num in enumerate(selected_files)}
    
    log_event(f"선택된 파일 목록: {selected_files}")
    
    # ThreadPoolExecutor를 사용한 멀티스레딩
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
        # Cache Server 인덱스 관리
        futures = {}
        for order, file_num in file_order_mapping.items():
            cache_server_index = order % len(CACHE_SERVERS)
            future = executor.submit(download_file, file_num, order, cache_server_index)
            futures[future] = order
        
        for future in as_completed(futures):
            order, file_num, file_size = future.result()
            with download_lock:
                download_results[order] = (file_num, file_size)
    
    # 결과를 파일 순서에 맞게 정렬
    sorted_results = [download_results[i] for i in sorted(download_results.keys())]
    
    # 로그 기록
    success_count = 0
    failure_count = 0
    total_file_size = 0
    total_time = 0
    for file_num, file_size in sorted_results:
        if file_size:
            log_event(f"파일 다운로드 성공: {file_num}, 크기: {file_size}KB")
            success_count += 1
            total_file_size += file_size
            total_time += file_size / 1  # 평균 속도: 1KB/ms (Data Server)
        else:
            log_event(f"파일 다운로드 실패: {file_num}")
            failure_count += 1
    
    average_time = total_time / success_count if success_count > 0 else 0
    log_event(f"총 다운로드 시도: {TOTAL_FILES}, 성공: {success_count}, 실패: {failure_count}")
    log_event(f"평균 파일 전송 시간: {average_time}ms")
    log_event(f"총 파일 전송 크기: {total_file_size}KB")
    
    # Graceful Termination
    log_event("모든 파일 다운로드 완료. 클라이언트 종료.")

if __name__ == "__main__":
    main()
