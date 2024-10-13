import socket
import time
import random
import logging

log_file1 = "client1.txt"
log_file2 = "client2.txt"
log_file3 = "client3.txt"
log_file4 = "client4.txt"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file1),
        logging.FileHandler(log_file2),
        logging.FileHandler(log_file3),
        logging.FileHandler(log_file4),
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)

DATA_SERVER_HOST = '34.68.170.234'
DATA_SERVER_PORT = 5000
MAX_FILES = 100  # 클라이언트가 수신할 파일 개수
DOWNLOAD_SPEED_FROM_DATA_SERVER = 1000  # 데이터 서버에서 다운로드 속도 (1 Mbps = 1000 kb/s)
DOWNLOAD_SPEED_FROM_CACHE_SERVER = 3000  # 캐시 서버에서 다운로드 속도 (3 Mbps = 3000 kb/s)
virtual_storage = {}  # 클라이언트가 받은 가상파일을 저장할 공간

buffer=''

# 랜덤 리스트 생성
def random_list():
    random_list = random.sample(range(1, 1001), MAX_FILES)  # 1~10,000 중 1,000개 파일 선택
    random_list.sort()  # 파일 리스트 정렬
    return random_list

# 랜덤 리스트 전송
def send_random_list(data_server_conn, random_list):
    random_list = ':'.join(map(str, random_list)) 
    random_msg = f"RANDOM:{random_list}\n"
    data_server_conn.sendall(random_msg.encode())
    print(f"데이터 서버로 랜덤 리스트 전송: {random_msg}")
    logging.debug(f"데이터 서버로 랜덤 리스트 전송: {random_msg}")

# 파일 데이터 수신 함수 ("\n"으로 구분하여 청크 단위로 수신)
def receive_file(socket):
    global buffer  # 전역 buffer 사용    
    
    while True:
        try:
            # buffer에 '\n'이 있으면, 메시지를 분리하여 반환
            if '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return message  # 메시지를 반환하고, 나머지는 buffer에 남겨 둠

            # 새 데이터를 수신하여 buffer에 추가
            chunk = socket.recv(4096).decode()
            if not chunk:
                break  # 연결 종료 시

            buffer += chunk  # 새로 받은 데이터를 buffer에 추가

            # buffer에 '\n'이 포함된 경우 메시지와 남은 데이터를 분리
            if '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return message  # 메시지를 반환하고, 나머지는 buffer에 남겨 둠

        except Exception as e:
            print(f"데이터 수신 중 오류 발생: {e}")
            logging.debug(f"데이터 수신 중 오류 발생: {e}")
            break


    # 수신된 파일 데이터를 문자열로 변환
    file_data_str = file_data.decode()

    # 수신한 데이터가 'FILE:'로 시작하는지 확인
    if file_data_str.startswith("FILE:"):
        parts = file_data_str.split(":")
        if len(parts) == 5:  # FILE:file_num:file_data:Max:request_cnt 형식에 맞는지 확인
            _, file_num, file_data, max_file_num, request_cnt = parts
            print(f"파일 번호: {file_num}, Max 파일 번호: {max_file_num}, 요청 횟수: {request_cnt}")
            print(f"파일 번호{file_num}, 파일 크기: {len(file_data)}")
            logging.debug(f"파일 번호: {file_num}, Max 파일 번호: {max_file_num}, 요청 횟수: {request_cnt}")
            logging.debug(f"파일 번호{file_num}, 파일 크기: {len(file_data)}")
            # 실제 파일 데이터 반환
            return file_data

    return None  # 형식이 맞지 않을 경우 None 반환


# 두 서버중 하나에 파일 요청(최적의 서버로)
def request_file(file_num, cache_conns, data_server_conn):
    # # 캐시 서버 우선 요청(기존 방식)
    # for cache_conn in cache_conns:
    #     if request_cache(cache_conn, file_num):
    #         return

    # 홀수 파일인 경우 첫 번째 캐시 서버에 요청
    if file_num % 2 != 0:
        if request_cache(file_num, cache_conns[0]): 
            return

    # 짝수 파일인 경우 두 번째 캐시 서버에 요청
    if file_num % 2 == 0:
        if request_cache(file_num, cache_conns[1]):
            return

    # 모든 캐시 서버에서 캐시 미스가 발생하면 데이터 서버에 요청
    print(f"{file_num}번 파일 모든 캐시 서버에서 캐시 미스 -> 데이터 서버로 요청")
    logging.debug(f"{file_num}번 파일 모든 캐시 서버에서 캐시 미스 -> 데이터 서버로 요청")
    request_data_server(file_num, data_server_conn)

# 캐시 서버에 파일 요청 (유지된 연결 사용)
def request_cache(file_num, cache_conn):
    try:
        request_msg = f"REQUEST:{file_num}\n"
        cache_conn.sendall(request_msg.encode()) 
        print(f"캐시 서버로 {file_num}번 파일 요청 중...")
        logging.debug(f"캐시 서버로 {file_num}번 파일 요청 중...")

        # 캐시 서버의 응답 수신
        response = receive_file(cache_conn)
        if response.startswith("Cache Hit"):
            print(f"캐시 히트 발생: {file_num}번 파일")
            logging.debug(f"캐시 히트 발생: {file_num}번 파일")

            # 데이터 수신 - FILE:file_num:file_data:Max:request_cnt 받음
            data = receive_file(cache_conn)  # 전체 메시지 수신 (청크 처리)
            virtual_storage[file_num] = data  # 가상 저장소에 파일 데이터 저장
            print(f"캐시 서버에서 파일 수신 완료: {file_num}번 파일")
            logging.debug(f"캐시 서버에서 파일 수신 완료: {file_num}번 파일")
            return True  # 파일 수신 성공
        
        elif response.startswith("Cache Miss"):
            print(f"캐시 미스 발생: {file_num}번 파일")
            logging.debug(f"캐시 미스 발생: {file_num}번 파일")
            return False  # 캐시 미스 발생
        else:
            print(f"알 수 없는 응답: {response}")
            logging.debug(f"알 수 없는 응답: {response}")
            return False  # 오류 처리
    
    except Exception as e:
        print(f"캐시 서버에서 파일 수신 중 오류 발생")
        logging.debug(f"캐시 서버에서 파일 수신 중 오류 발생")
        return False  # 파일 수신 실패

# 데이터 서버에 파일 요청
def request_data_server(file_num, data_server_conn):
    try:
        request_msg = f"REQUEST:{file_num}\n"
        data_server_conn.sendall(request_msg.encode())
        print(f"데이터 서버에 {file_num}번 파일 요청 전송")
        logging.debug(f"데이터 서버에 {file_num}번 파일 요청 전송")
        
        # 데이터 수신 - FILE:file_num:file_data:Max:request_cnt 받음
        data = receive_file(data_server_conn)  # 전체 메시지 수신 (청크 처리)
        virtual_storage[file_num] = data  # 가상 저장소에 파일 데이터 저장
       
        print(f"데이터 서버에서 파일 수신 완료: {file_num}번 파일")
        logging.debug(f"데이터 서버에서 파일 수신 완료: {file_num}번 파일")
    except Exception as e:
        print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")
        logging.debug(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")

def start_client():
    # 데이터 서버에 연결하여 캐시 서버 정보 수신
    data_server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 데이트 서버에서 연결 유지
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결되었습니다.")
        logging.debug(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결되었습니다.")
        
        # 캐시 서버 정보를 수신
        cache_servers = []
        data = data_server_conn.recv(1024).decode()
        server_info = data.strip().split(':')  # ':'으로 구분

        # IP와 포트는 짝으로 구성되므로 두 개씩 처리
        for i in range(0, len(server_info)):
            # 문자열에서 IP와 포트 번호 추출
            info = server_info[i].split(", ")
            cache_host = info[0].strip("('")  # IP 주소 추출
            cache_port = int(info[1])         # 포트 번호 추출
            cache_servers.append((cache_host, cache_port))  # 튜플로 (IP, 포트)를 리스트에 저장

    except Exception as e:
        print(f"데이터 서버에 연결하여 캐시 서버 정보 수신 중 오류 발생: {e}")
        logging.debug(f"데이터 서버에 연결하여 캐시 서버 정보 수신 중 오류 발생: {e}")

    print(f"수신한 캐시 서버 정보: {cache_servers}")
    logging.debug(f"수신한 캐시 서버 정보: {cache_servers}")

 
    
    # 두 개의 캐시 서버에 각각 연결을 유지
    cache_conns = []
    for cache_host, cache_port in cache_servers:
        cache_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cache_conn.connect(('127.0.0.1', cache_port))  # IP와 포트로 캐시 서버 연결
        cache_conns.append(cache_conn)
        print(f"캐시 서버 {'127.0.0.1'}:{cache_port}에 연결 유지")
        logging.debug(f"캐시 서버 {'127.0.0.1'}:{cache_port}에 연결 유지")

    file_request_list = random_list() #랜덤 리스트 생성
    send_random_list(data_server_conn, file_request_list) #랜덤 리스트 데이터 서버에 전송

    #데이터 서버에게 FLAG:1을 받으면 요청 시작
    flag_msg = data_server_conn.recv(4096).decode()
    if flag_msg == "FLAG:1\n":
        print("데이터 서버에서 FLAG:1 수신. 파일 요청 시작.")
        logging.debug("데이터 서버에서 FLAG:1 수신. 파일 요청 시작.")
        # 랜덤 1,000개 파일 요청
        # for file_num in file_request_list:
        #     request_file(file_num, cache_conns,data_server_conn)
        #     # 데이터, 캐시 서버와 연결 유지

        while file_request_list:
            if random.random() < 0:  # 0% 확률
                file_num = file_request_list.pop(-1)  # 리스트에서 가장 큰 파일
                print(f"20% 확률로 가장 큰 파일 {file_num} 요청 중...")
                logging.debug(f"20% 확률로 가장 큰 파일 {file_num} 요청 중...")
            else:
                file_num = file_request_list.pop(0)  # 리스트에서 가장 작은 파일
                print(f"가장 작은 파일 {file_num} 요청 중...")
                logging.debug(f"가장 작은 파일 {file_num} 요청 중...")

            # 파일 요청 처리
            request_file(file_num, cache_conns, data_server_conn)

        print("모든파일 수신 완료")
        logging.debug("모든파일 수신 완료")

        #Gracefully Termination
        for cache_conn in cache_conns:
            cache_conn.close()  # 캐시 서버와의 연결 종료

        data_server_conn.close()  # 데이터 서버와의 연결 종료
        print("모든 연결 종료")
        logging.debug("모든 연결 종료")
        

if __name__ == "__main__":
    start_client()
