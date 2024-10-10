import socket
import time
import random

DATA_SERVER_HOST = '127.0.0.1'
DATA_SERVER_PORT = 5000
MAX_FILES = 1000  # 클라이언트가 수신할 파일 개수
DOWNLOAD_SPEED_FROM_DATA_SERVER = 1000  # 데이터 서버에서 다운로드 속도 (1 Mbps = 1000 kb/s)
DOWNLOAD_SPEED_FROM_CACHE_SERVER = 3000  # 캐시 서버에서 다운로드 속도 (3 Mbps = 3000 kb/s)
virtual_storage = {}  # 클라이언트가 받은 가상파일을 저장할 공간

# 랜덤 리스트 생성
def random_list():
    random_list = random.sample(range(1, 10001), MAX_FILES)  # 1~10,000 중 1,000개 파일 선택
    random_list.sort()  # 파일 리스트 정렬
    return random_list

# 랜덤 리스트 전송
def send_random_list(data_server_conn, random_list):
    random_list = ':'.join(map(str, random_list)) 
    random_msg = f"RANDOM:{random_list}"
    data_server_conn.sendall(random_msg.encode())
    print(f"데이터 서버로 랜덤 리스트 전송: {random_msg}")

# 파일 데이터 수신 함수 ("\n"으로 구분하여 청크 단위로 수신)
def receive_file(conn):
    file_data = b''  # 파일 데이터를 저장할 변수
    while True:
        chunk = conn.recv(4096)  # 한 번에 최대 4096 바이트 수신
        if not chunk:
            break

        file_data += chunk
        if b'\n' in chunk:  # "\n"이 수신되면 데이터 끝으로 간주
            break

    # "\n" 제거
    if file_data.endswith(b'\n'):
        file_data = file_data[:-1]  # 마지막 "\n" 제거

    print(f"수신된 데이터 크기: {len(file_data)} 바이트")

    # 수신된 파일 데이터를 문자열로 변환
    file_data_str = file_data.decode()

    # 수신한 데이터가 'FILE:'로 시작하는지 확인
    if file_data_str.startswith("FILE:"):
        parts = file_data_str.split(":")
        if len(parts) == 5:  # FILE:file_num:file_data:Max:request_cnt 형식에 맞는지 확인
            _, file_num, file_data, max_file_num, request_cnt = parts
            print(f"파일 번호: {file_num}, Max 파일 번호: {max_file_num}, 요청 횟수: {request_cnt}")

            # 실제 파일 데이터 반환
            return file_data

    return None  # 형식이 맞지 않을 경우 None 반환


# 두 서버중 하나에 파일 요청(최적의 서버로)
def request_file(file_num, cache_conns, data_server_conn):
    # # 캐시 서버 우선 요청(기존 방식)
    # for cache_conn in cache_conns:
    #     if request_cache(cache_conn, file_num):
    #         return

    # 첫 번째 캐시 서버(홀수 파일 관리)
    if file_num % 2 != 0:
        if request_cache(file_num, cache_conns[0], is_odd_server=True):
            return

    # 두 번째 캐시 서버(짝수 파일 관리)
    if file_num % 2 == 0:
        if request_cache(file_num, cache_conns[1], is_odd_server=False):
            return

    # 모든 캐시 서버에서 캐시 미스가 발생하면 데이터 서버에 요청
    print(f"{file_num}번 파일 모든 캐시 서버에서 캐시 미스 -> 데이터 서버로 요청")
    request_data_server(file_num, data_server_conn)

# 캐시 서버에 파일 요청 (유지된 연결 사용)
def request_cache(file_num, cache_conn,is_odd_server=True):
    try:
        # 홀수 캐시 서버와 짝수 캐시 서버를 구분
        if is_odd_server and file_num % 2 == 0:
            print(f"홀수 파일 캐시 서버에 짝수 파일 {file_num} 요청 불가.")
            return False  # 짝수 파일은 홀수 서버에 요청할 수 없음
        if not is_odd_server and file_num % 2 != 0:
            print(f"짝수 파일 캐시 서버에 홀수 파일 {file_num} 요청 불가.")
            return False  # 홀수 파일은 짝수 서버에 요청할 수 없음

        request_msg = f"REQUEST:{file_num}"
        cache_conn.sendall(request_msg.encode()) 
        print(f"캐시 서버로 {file_num}번 파일 요청 중...")

        # 캐시 서버의 응답 수신
        response = cache_conn.recv(4096).decode()
        if response == "Cache Hit":
            print(f"캐시 히트 발생: {file_num}번 파일")

            # 데이터 수신 - FILE:file_num:file_data:Max:request_cnt 받음
            data = receive_file(cache_conn)  # 전체 메시지 수신 (청크 처리)
            virtual_storage[file_num] = data  # 가상 저장소에 파일 데이터 저장
            print(f"캐시 서버에서 파일 수신 완료: {file_num}번 파일")
            return True  # 파일 수신 성공
        
        elif response == "Cache Miss":
            print(f"캐시 미스 발생: {file_num}번 파일")
            return False  # 캐시 미스 발생
        else:
            print(f"알 수 없는 응답: {response}")
            return False  # 오류 처리
    
    except Exception as e:
        print(f"캐시 서버에서 파일 수신 중 오류 발생")
        return False  # 파일 수신 실패

# 데이터 서버에 파일 요청
def request_data_server(file_num, data_server_conn):
    try:
        request_msg = f"REQUEST:{file_num}"
        data_server_conn.sendall(request_msg.encode())
        print(f"데이터 서버에 {file_num}번 파일 요청 전송")
        
        # 데이터 수신 - FILE:file_num:file_data:Max:request_cnt 받음
        data = receive_file(data_server_conn)  # 전체 메시지 수신 (청크 처리)
        virtual_storage[file_num] = data  # 가상 저장소에 파일 데이터 저장
       
        print(f"데이터 서버에서 파일 수신 완료: {file_num}번 파일")
    except Exception as e:
        print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")

def start_client():
    # 데이터 서버에 연결하여 캐시 서버 정보 수신
    data_server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 데이트 서버에서 연결 유지
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결되었습니다.")
        
        # 캐시 서버 정보를 수신
        cache_servers = []
        data = data_server_conn.recv(1024).decode()
        
        # 수신된 캐시 서버 정보를 문자열로 처리하여 올바른 형식으로 변환
        server_info = data.strip().split(',')
        for server in server_info:
            # 문자열에서 IP와 포트 추출
            cache_host, cache_port = server.replace("(", "").replace(")", "").replace("'", "").split(',')
            cache_servers.append((cache_host.strip(), int(cache_port.strip())))  # 포트를 정수로 변환하여 저장
    except Exception as e:
        print(f"데이터 서버에 연결하여 캐시 서버 정보 수신 중 오류 발생: {e}")
        cache_servers = []

    print(f"수신한 캐시 서버 정보: {cache_servers}")

    # 두 개의 캐시 서버에 각각 연결을 유지
    cache_conns = []
    for cache_host, cache_port in cache_servers:
        cache_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cache_conn.connect((cache_host, cache_port))  # IP와 포트로 캐시 서버 연결
        cache_conns.append(cache_conn)
        print(f"캐시 서버 {cache_host}:{cache_port}에 연결 유지")

    # 랜덤 1,000개 파일 요청
    file_request_list = random_list()  # 랜덤 파일 리스트 생성
    for file_num in file_request_list:
        request_file(file_num, cache_conns,data_server_conn)
        # 데이터, 캐시 서버와 연결 유지


if __name__ == "__main__":
    start_client()
