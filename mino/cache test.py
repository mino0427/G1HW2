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

# 캐시 서버 안에 있는 가장 큰 파일 번호(크기)
Max = 0
FLAG = 0  # 기본값 0, 데이터 서버에서 받은 FLAG에 따라 변경

# 캐시 용량 제한 (25MB)
CACHE_CAPACITY_KB = 25 * 1024 # 25MB를 KB로 변환

cache = {}
cache_size = 0  # 현재 캐시 사용량 (KB)
free_space = 0

# 데이터 서버 연결 설정
data_server_socket = None
data_server_lock = threading.Lock()

buffer=''#버퍼 역할을 한다

def connect_to_data_server(host, port):
    global data_server_socket
    try:
        # if data_server_socket is None:
        data_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_server_socket.connect((host, port))
        print(f"데이터 서버 {host}:{port}에 연결되었습니다.")
    except Exception as e:
        print(f"데이터 서버에 연결 중 오류 발생: {e}")
        data_server_socket = None

# 파일 전송 시간 계산 및 전송 처리
def send_file(conn, file_num, file_data, request_cnt, max_file_num):
    global cache_size

    # 파일 전송 메시지 생성
    header_message = f"FILE:{file_num}:"
    tail_message = f":{max_file_num}:{request_cnt}"

    full_message = header_message + file_data + tail_message +"\n"
    
    # 실제 파일 데이터 전송
    total_bytes = len(full_message)
    sent_bytes = 0
    while sent_bytes < total_bytes:
        chunk_size = min(4096, total_bytes - sent_bytes)
        chunk = full_message[sent_bytes:sent_bytes + chunk_size].encode() # 수정한 부분
        conn.sendall(chunk)
        sent_bytes += chunk_size

    conn.sendall(f"MSG:파일 전송 완료 {file_num} KB\n".encode())
    
    # request_cnt 감소 및 캐시 정리
    with cache_lock:
        if file_num in cache:
            # 캐시에서 파일 데이터와 정보를 가져옴
            file_data, request_cnt = cache[file_num]
            # request_cnt 값을 1 감소
            request_cnt -= 1
            print(f"파일 {file_num}의 request_cnt 감소: {request_cnt}")

            # request_cnt가 0이면 캐시에서 해당 파일 삭제
            if request_cnt <= 0:
                del cache[file_num]
                cache_size -= file_num
                print(f"파일 {file_num}의 request_cnt가 0이 되어 캐시에서 제거되었습니다. 현재 캐시 사용량: {cache_size} KB")
            else:
                # request_cnt 업데이트
                cache[file_num] = (file_data, request_cnt)

# 데이터 서버에서 파일을 요청하는 함수
def request_from_data_server(): 
        global cache_size, Max, FLAG

        while FLAG==0:
            try:
                # free_space = CACHE_CAPACITY_KB - cache_size
                message = receive_data(data_server_socket)
            
               
                # file 데이터로 받아야됌
                if message.startswith("FILE:"):
                    # 파일 데이터 수신
                    try:
                        # 1. FILE 번호와 그 이후의 데이터를 분리
                        parts = message.split(":")
                        if len(parts) < 4:
                            raise ValueError("잘못된 메시지 형식")

                        file_num = int(parts[1])  # 파일 번호
                        file_data_and_tail = ":".join(parts[2:])  # 파일 데이터와 그 뒤의 정보

                        # 2. tail 부분에서 request_cnt 추출
                        tail_index = file_data_and_tail.rfind(":")  # tail에서 request_cnt 전 마지막 구분자 위치 찾기
                        tail = file_data_and_tail[tail_index + 1:]  # 마지막 구분자 뒤의 request_cnt 추출
                        request_cnt = int(tail)
                        file_data,max_file_num,a = file_data_and_tail.split(':')  # 파일 데이터는 마지막 구분자 이전까지
                        
                        # 3. max_file_num추출
                        
                        max_file_num = int(max_file_num)
                        Max = max_file_num
                    
                    except Exception as e:
                        print(f"데이터 서버에서 파일 수신 중 오류")
                
                elif message.startswith("FLAG:"):
                    # 정확한 문자열 비교를 수행
                    _, flag_value = message.split(":")
                    if flag_value.strip() == "1":
                        FLAG = 1
                        print("FLAG 1을 수신했습니다.")
                        break
                    
                if file_data:
                    with cache_lock:
                        cache[file_num] = (file_data, request_cnt)
                        cache_size += file_num
                        free_space = CACHE_CAPACITY_KB - cache_size
                        print(f"cache_size: {cache_size}, 데이터 서버로 부터 받은 파일: {file_num}, 남은 공간: {free_space}")                

            except Exception as e:
                print(f"초기 데이터 수신 중 오류 발생: {e}")
                break
       
        while flag_value == 1 and free_space >= Max: 
            try:
                print(f"free_space({free_space} KB) >= Max({Max}) 조건 만족")
                with data_server_lock:
                    try:
                        data_server_socket.sendall(f"REQUEST:{file_num}".encode())
                        print(f"데이터 서버에 {file_num}번 파일 요청 전송")
                        # 데이터 서버로부터 파일 수신
                        data = receive_data(data_server_socket)

                        message = data.decode(errors='ignore')

                        if message.startswith("FILE:"):
                            # 파일 데이터 수신
                            try:
                                _, file_num, file_data, max_file_num, request_cnt = message.split(":", 4)[0:4], data[len("FILE:{file_num}:".format(file_num=file_num)):]
                                file_num = int(file_num)
                                max_file_num = int(max_file_num)
                                request_cnt = int(request_cnt)
                                file_data = file_data.encode()

                                Max = max_file_num
                            
                                # 캐시 용량 검사 및 파일 저장
                                with cache_lock:
                                    if cache_size + file_num <= CACHE_CAPACITY_KB:
                                        cache[file_num] = (file_data, request_cnt)
                                        cache_size += file_num
                                        free_space = CACHE_CAPACITY_KB - cache_size
                                        print(f"파일 {file_num}을(를) 캐시에 저장했습니다. 현재 캐시 사용량: {cache_size} KB")
                                    else:
                                        print(f"캐시 용량 부족으로 파일 {file_num}을(를) 캐시에 저장하지 못했습니다.")
                            except ValueError as e:
                                print(f"파일 메시지 파싱 중 오류 발생: {e}")
                                return None, None    
                        
                        # FLAG 메시지 처리
                        elif message.startswith("FLAG:"):
                            # ':'로 구분하여 FLAG 값 추출
                            _, flag_value = message.split(":")
                            if flag_value.strip() == "0":
                                FLAG = 0
                                print("FLAG 0을 수신했습니다 - 작업 종료.")
                                break
                                             
                        else:
                            print(f"알 수 없는 데이터 서버 응답: {message}")
                            return None, None
                    except Exception as e:
                        print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")
                        return None, None
            except Exception as e:
                print(f"데이터 서버에서 파일 수신 중 오류 발생: {e}")
                break

def receive_data(socket):
    global buffer  # 전역 buffer 사용

    while True:
        try:
            # buffer에 '\n'이 있으면, 메시지를 분리하여 반환
            if '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return message  # 메시지를 반환하고, 나머지는 buffer에 남겨 둠

            # 새 데이터를 수신하여 buffer에 추가
            chunk = socket.recv(4096).decode()

            # if isinstance(chunk, bytes):
            #     chunk = chunk.decode(errors='ignore')

            if not chunk:
                break  # 연결 종료 시

            buffer += chunk  # 새로 받은 데이터를 buffer에 추가

            # buffer에 '\n'이 포함된 경우 메시지와 남은 데이터를 분리
            if '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return message  # 메시지를 반환하고, 나머지는 buffer에 남겨 둠

        except Exception as e:
            print(f"데이터 수신 중 오류 발생: {e}")
            break


def handle_client(conn, addr):
    global FLAG
    print(f"연결된 클라이언트: {addr}")
    ###############################FLAG가 0인 경우 그냥 이 부분을 넘어가버림#############수정필요################
    # FLAG = receive_data(data_server_socket)## 내가 수정한 부분
    
    # 데이터를 수신하여 FLAG 값을 확인
    while True:
        if FLAG==1:
            break

    if FLAG == 1:
        print("데이터 서버에서 FLAG:1 수신. 파일 요청 시작.")

        while FLAG:
            message = receive_data(conn)

            
            # 메시지와 파일, 요청 구분
            if message.startswith("REQUEST:"):
                _, file_num = message.strip().split(":")
                file_num = int(file_num)
                print(f"클라이언트로부터 파일 {file_num} 요청 수신")

            # 캐시에 있는지 확인
                with cache_lock:
                    if file_num in cache:
                        #캐시 히트
                        file_data, request_cnt = cache[file_num]
                        conn.sendall("Cache Hit".encode())
                        send_file(conn, file_num,file_data, request_cnt,Max)
                        print(f"Cache Hit: {file_num}번 파일 캐시에서 {CACHE_TO_CLIENT_SPEED}로 전송")
                    else:
                        # 캐시 미스
                        conn.sendall("Cache Miss".encode())
                        print(f"Cache Miss: {file_num}번 파일 캐시에 없음, 데이터 서버로 요청")
                        
    conn.close()
    print(f"클라이언트 연결 종료: {addr}")

# 데이터 서버 연결 종료 함수
def close_data_server_connection():
    global data_server_socket
    if data_server_socket:
        data_server_socket.close()
        data_server_socket = None
        print("데이터 서버와의 연결이 종료되었습니다.")
    
    #flag추가

def start_cache_server():
    global cache_lock
    cache_lock = threading.Lock()

    # 데이터 서버에 연결
    connect_to_data_server(DATA_SERVER_HOST, DATA_SERVER_PORT)
    print(f"데이터 서버 {DATA_SERVER_HOST}:{DATA_SERVER_PORT}에 연결")
    
    try:
        # 캐시 서버 소켓 설정 (자동 포트 할당)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, 0))  # 운영체제가 자동으로 사용 가능한 포트 할당
        cache_port = server.getsockname()[1]  # 할당받은 포트 번호 확인
        print(f"캐시 서버의 할당된 포트 번호: {cache_port}")

        # 데이터 서버에 캐시 서버 포트 번호 전송
        data_server_socket.sendall(f"{cache_port}".encode())

    except Exception as e:
        print(f"데이터 서버 연결 중 예외 발생: {e}")
        return
    
    ###################cache 초기화################################################################3333    
    thread = threading.Thread(target=request_from_data_server)
    thread.start()
        
        
     #########################################데이터 서버와 연결 완료 시점######################################3
        
    # 캐시 서버 실행
    server.listen()
    print(f"Cache_server가 {HOST}:{cache_port}에서 실행 중입니다.")

    for i in range(0,4):#####수정함 이렇게 해도 되겠지?#####################여기서 4개 받고 끝이 아니라 계속 accept 대기 하고 있는 건가?#########
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
    
    #################데이터 서버와 클라이언트 모두 연결 완료 시점####################################################################################

if __name__ == "__main__":
    start_cache_server()