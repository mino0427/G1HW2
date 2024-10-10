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
cache_key_sum = 0  # 캐시의 키 값들의 합

# 파일 전송 시간 계산 및 전송 처리
def send_file(conn, file_num, file_data, file_size_kb, speed_kbps, request_cnt, max_file_num):
    global cache_key_sum

    # 파일 전송 메시지 생성
    header_message = f"FILE:{file_num}"
    tail_message = f"{max_file_num}:{request_cnt}"

    full_message = header_message + file_data + tail_message +"\n"
    # 전송 시간 계산
    transfer_time = file_size_kb * 8 / speed_kbps  # 전송에 필요한 시간 계산
    time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 실제 파일 데이터 전송
    total_bytes = len(file_data)
    sent_bytes = 0
    while sent_bytes < total_bytes:
        chunk_size = min(4096, total_bytes - sent_bytes)
        chunk = file_data[sent_bytes:sent_bytes + chunk_size].encode()
        conn.sendall(chunk)
        sent_bytes += chunk_size

    conn.sendall(f"MSG:파일 전송 완료 {file_size_kb} kb\n".encode())
    # conn.sendall(file_data)  # 실제 파일 데이터 전송

# 데이터 서버에서 파일을 요청하는 함수
def request_from_data_server(file_num):
        global cache_size

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))

            data = s.recv(4096)
            if not data:
                return None, None
            print(f"데이터 서버로부터 응답이 없습니다.")
            message = data.decode(errors='ignore')

            if message.startswith("FILE:"):
                # 파일 데이터 수신
                _, file_num, file_data, max_file_num, request_cnt = message.split(":", 4)[0:4], data[len("FILE:{file_num}:".format(file_num=file_num)):]
                received_file_num = int(received_file_num)
                max_file_num = int(max_file_num)
                request_cnt = int(request_cnt)
                file_data = file_data.encode()
            
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
                conn.sendall(f"MSG:이 캐시 서버는 홀수 번호의 파일만 처리합니다.\n".encode())
                continue
            elif cache_server_number == 2 and file_num % 2 != 0:
                conn.sendall(f"MSG:이 캐시 서버는 짝수 번호의 파일만 처리합니다.\n".encode())
                continue
        # 캐시에 있는지 확인
            with cache_lock:
                if file_num in cache:
                    #캐시 히트
                    conn.sendall("MSG:Cache Hit\n".encode())
                    file_data, file_size_kb = cache[file_num]
                    file_size_kb = cache[file_num]
                    send_file(conn, file_data, file_size_kb, CACHE_TO_CLIENT_SPEED)
                    print(f"Cache Hit: {file_num}번 파일 캐시에서 {CACHE_TO_CLIENT_SPEED}로 전송")
                else:
                    # 캐시 미스
                    conn.sendall("MSG:Cache Miss\n".encode())
                    print(f"Cache Miss: {file_num}번 파일 캐시에 없음, 데이터 서버로 요청")

        elif message.startswith("FILE:"):
            try:
                _, file_num, file_data, max_file_num, request_cnt = message.split(":", 4)
                file_num = int(file_num)
                max_file_num = int(max_file_num)
                request_cnt = int(request_cnt)
                file_data = file_data.encode()  # 파일 데이터를 바이트 형식으로 변환

                file_size_kb = len(file_data) // 1024  # 바이트를 KB로 변환

                # Max 값을 업데이트
                with cache_lock:
                    if max_file_num > Max:
                        Max = max_file_num
                        print(f"Max 값이 {Max}로 업데이트되었습니다.")
                    # 딕셔너리
                    if cache_size + file_size_kb <= CACHE_CAPACITY_KB:
                        # 파일 번호를 키로 하고, [file_data, request_cnt] 리스트를 값으로 저장
                        cache[file_num] = [file_data, request_cnt]
                        cache_size += file_size_kb
                        print(f"파일 {file_num}을(를) 캐시에 저장했습니다. 현재 캐시 사용량: {cache_size} KB")

                    # 리스트로 바꿨을 때 사용
                    # if cache_size + file_size_kb <= CACHE_CAPACITY_KB:
                    #     cache.append() = ([file_num, file_data, request_cnt])
                    #     cache_size += file_size_kb
                    #     print(f"파일 {file_num}을(를) 캐시에 저장했습니다. 현재 캐시 사용량: {cache_size} KB")
                    else:
                        print(f"캐시 용량 부족으로 파일 {file_num}을(를) 캐시에 저장하지 못했습니다.")
            except ValueError as e:
                print(f"파일 메시지 파싱 중 오류 발생: {e}")
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
            _, number = response.split(":")
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

# 전역변수 Max 선언 O
# 데이터 서버에 파일을 받을 때 계속 max값 업데이트 하기 O
# 형식-> FILE:file_num:file_data:Max:request_cnt O (설명 파일 데이터 전송 시 , FILE: 파일 번호 : 파일 데이터:캐시에 보내지는 파일 중 가장 크기가 큰 파일 번호)

# 해야할일
# 데이터 서버에 파일을 요청할 때 조건 만들기
# (25MB(캐시 서버 용량) - cache{} list에 모든 파일 번호들의 합 > max_file_num
# 데이터 서버에서 받은 max_file_num(데이터 서버에서는 최솟값)
# 데이터 서버에서 파일 중복 개수(count)가 0이 될 때마다, max_file_num를 다운 받을 수 있는지 확인한다
# 딕셔너리 키값 계산 법 -> cache_key_sum (변수명) = sum(cache.keys())

# 캐시를 딕셔너리로 해보고 안되면 리스트로 바꾸기 (일단 딕셔너리로 하는중)
# 캐시1은 홀수 캐시2는 짝수 파일 넘버를 관리

# request from data server
# 파일 요청 조건은 캐시 서버 용량 - 캐시 딕셔너리의 키 값들의 합 > Max file num (용량 확인 계산)
# 데이터 서버에서 행렬이 0이아닌 최솟값을 파일 넘버만 받아서 캐시서버에 max file num으로 저장한다.
# 용량확인 계산을 하고 조건을 만족했을 때 요청

# 파일 요청 시에도 캐시1은 홀수 파일 넘버의 파일을 요청해야하고
# 캐시2는 짝수 파일 넘버의 파일을 데이터 서버에 요청한다.

# receive data
# starts with request ㅡ 클라이언트에게 요청을 받으면 캐시1은 홀수 파일을 클라이언트가 요청 하는데로 전송하고, 캐시2는 짝수 파일을 전송한다
# request cnt가 0이 된 값은 delete를 하고
# request cnt가 0이 될 때마다 delete되고 남아있는 딕셔너리의 키 값들을 더해서 용량 확인 계산을 한다