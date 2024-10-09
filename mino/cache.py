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

# 캐시 서버 번호 및 최대 캐시 서버 수
MAX_CACHE_SERVERS = 2
cache_server_number = None  # 캐시 서버 번호 (1 또는 2)

# 캐시 서버 안에 있는 가장 큰 파일 번호(크기)
Max = 0

# 캐시 용량 제한 (25MB)
CACHE_CAPACITY_KB = 25 * 1024  # 25MB를 KB로 변환

cache = {}
cache_size = 0  # 현재 캐시 사용량 (KB)

# 파일 전송 시간 계산 및 전송 처리
def send_file(conn, file_num, file_data, file_size_kb, speed_kbps):
    # 파일 전송 메시지 생성
    message = f"FILE:{file_num}:".encode() + file_data + Max
    # 전송 시간 계산
    transfer_time = file_size_kb * 8 / speed_kbps  # 전송에 필요한 시간 계산
    time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 실제 파일 데이터 전송
    total_bytes = len(file_data)
    sent_bytes = 0
    while sent_bytes < total_bytes:
        chunk_size = min(4096, total_bytes - sent_bytes)
        chunk = file_data[sent_bytes:sent_bytes + chunk_size]
        conn.sendall(chunk)
        sent_bytes += chunk_size

    conn.sendall(f"MSG:파일 전송 완료 {file_size_kb} kb".encode())
    conn.sendall(file_data)  # 실제 파일 데이터 전송

# 데이터 서버에서 파일을 요청하는 함수  <-이 부분에 Max + 2(홀 짝이니까)와 zero_request_list에 저장된 파일 번호의 총합(=파일의 사이즈 총합)이 데이터 서버로 부터 받을 파일의 크기보다 크다면 zero_request_list를 비우고, 데이터 서버에 새로운 파일을 요청한다.
def request_from_data_server(file_num):
        global cache_size

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
            s.sendall(f"REQUEST:{file_num}".encode())

            data = s.recv(4096)
            if not data:
                return None, None
            print(f"데이터 서버로부터 응답이 없습니다.")
            message = data.decode(errors='ignore')

            if message.startswith("FILE:"):
                # 파일 데이터 수신
                header, file_data = message.split(":", 2)[0:2], data[len("FILE:{file_num}:".format(file_num=file_num)):]
                _, received_file_num = header.split(":")
                received_file_num = int(received_file_num)
            
                if received_file_num != file_num:
                    print(f"받은 파일 번호가 요청한 파일 번호와 다릅니다.")
                    return None, None

                file_size_kb = len(file_data) // 1024  # 바이트를 KB로 변환
            
                # 캐시 용량 검사 및 파일 저장
                with cache_lock:
                    if cache_size + file_size_kb <= CACHE_CAPACITY_KB:
                        cache[file_num] = (file_data, file_size_kb)
                        cache_size += file_size_kb
                        print(f"파일 {file_num}을(를) 캐시에 저장했습니다. 현재 캐시 사용량: {cache_size} KB")
                    else:
                        print(f"캐시 용량 부족으로 파일 {file_num}을(를) 캐시에 저장하지 못했습니다.")
                return file_data, file_size_kb
            elif message.startswith("MSG:"):
                print(f"데이터 서버 메시지: {message}")
                return None, None
            else:
                print(f"알 수 없는 데이터 서버 응답: {message}")
                return None, None
        except Exception as e:
            print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")
            return None, None

def handle_client(conn, addr):
    print(f"연결된 클라이언트: {addr}")

    def receive_data():
        data = b''
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                # 메시지 끝을 확인하기 위해 줄바꿈 또는 특정 구분자를 사용할 수 있습니다.
                if b'\n' in chunk:
                    break
            except:
                break
        return data
    
    while True:
        data = receive_data()
        if not data:
            break
        message = data.decode(errors='ignore')
        
        # 메시지와 파일, 요청 구분
        if message.startswith("REQUEST:"):
            _, file_num = message.strip().split(":")
            file_num = int(file_num)
            print(f"클라이언트로부터 파일 {file_num} 요청 수신")

            # 파일 번호에 따른 캐시 서버 역할 확인
            if cache_server_number == 1 and file_num % 2 == 0:
                conn.sendall(f"MSG:이 캐시 서버는 홀수 번호의 파일만 처리합니다.".encode())
                continue
            elif cache_server_number == 2 and file_num % 2 != 0:
                conn.sendall(f"MSG:이 캐시 서버는 짝수 번호의 파일만 처리합니다.".encode())
                continue
        # 캐시에 있는지 확인
            with cache_lock:
                if file_num in cache:
                    #캐시 히트
                    conn.sendall("MSG:Cache Hit".encode())
                    file_data, file_size_kb = cache[file_num]
                    file_size_kb = cache[file_num]
                    send_file(conn, file_data, file_size_kb, CACHE_TO_CLIENT_SPEED)
                    print(f"Cache Hit: {file_num}번 파일 캐시에서 {CACHE_TO_CLIENT_SPEED}로 전송")
                else:
                    # 캐시 미스
                    conn.sendall("MSG:Cache Miss".encode())
                    print(f"Cache Miss: {file_num}번 파일 캐시에 없음, 데이터 서버로 요청")
    conn.close()
    print(f"클라이언트 연결 종료: {addr}")

def start_cache_server():
    global cache_lock
    cache_lock = threading.Lock()

    # 먼저 데이터 서버와 연결
    data_server_conn =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결 시도 중...")
        data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))
        print("데이터 서버 연결 완료!")

        # 데이터 서버로부터 캐시 서버 번호 할당
        data_server_conn.sendall("REQUEST_CACHE_SERVER_NUMBER".encode())
        response = data_server_conn.recv(1024).decode()
        if response.startswith("CACHE_SERVER_NUMBER:"):
            _, number = response.strip().split(":")
            cache_server_number = int(number)
            print(f"캐시 서버 번호 할당 받음: {cache_server_number}")
        else:
            print("캐시 서버 번호를 할당받지 못했습니다.")
            data_server_conn.close()
            return

        if cache_server_number > MAX_CACHE_SERVERS:
            print(f"최대 캐시 서버 수({MAX_CACHE_SERVERS})를 초과했습니다.")
            data_server_conn.close()
            return

        # 캐시 서버 소켓 설정 (자동 포트 할당)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, 0))  # 운영체제가 자동으로 사용 가능한 포트 할당
        cache_port = server.getsockname()[1]  # 할당받은 포트 번호 확인
        print(f"캐시 서버의 할당된 포트 번호: {cache_port}")

        # 데이터 서버에 캐시 서버 포트 번호 전송
        data_server_conn.sendall(f"CACHE_SERVER_INFO:{cache_port}".encode())
    except Exception as e:
        print(f"데이터 서버 연결 중 예외 발생: {e}")
        return
        
    # 캐시 서버 실행
    server.listen()
    print(f"Cache_server {cache_server_number}가 {HOST}:{cache_port}에서 실행 중입니다.")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_cache_server()

# 해야할일
# 전역변수 Max 선언 O
# 데이터 서버에 파일을 요청할 때 조건 만들기 (25MB(캐시 서버 용량) - cache{} list에 모든 파일 번호들의 합 > Max + 2 일때, 데이터 서버에 파일 요청)
# 데이터 서버에서 파일 중복 개수(count)가 0이 될 때마다, Max + 2를 다운 받을 수 있는지 확인한다
# 데이터 서버에 파일을 받을 때 계속 max값 업데이트 하기
# 형식-> FILE:file_num:file_data:Max (설명 파일 데이터 전송 시 , FILE: 파일 번호 : 파일 데이터:캐시에 보내지는 파일 중 가장 크기가 큰 파일 번호)
