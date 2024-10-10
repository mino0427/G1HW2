import socket
import threading
import time


HOST = '0.0.0.0'
PORT = 5000
MAX_CLIENTS = 4  # 클라이언트 4개 대기

# 전송 속도 설정 (초당 전송되는 kb 수)
DATA_TO_CLIENT_SPEED = 1000  # kb단위로 가야함
DATA_TO_CACHE_SPEED = 2000

cache_servers = []  # 캐시 서버 정보 저장 (IP, Port)
client_conns = []  # 클라이언트 연결 저장
virtual_files = {}  # 가상 파일 저장 (파일 번호: 파일 크기)

data_array = [0] * 10001 #클라이언트의 요청 횟수를 저장한다.
FLAG=1 #프로그램 시작과 종료를 알리는 FLAG 변수(1: 시작, 0: 종료)
Max=[2,1] #Max[0]은 짝수 캐시에 보낸 가장 큰 파일 번호, Max[1]은 홀수 캐시에 보낸 가장 큰 파일 번호
next_min = [None, None]  # next_min은 캐시에게 보낼 다음 파일 번호(0: 짝수, 1: 홀수)
processed_file=0

virtual_files_lock = threading.Lock()
# 가상 파일 생성
def create_virtual_files():
    print("가상 파일 생성 시작...")
    with virtual_files_lock:
        for file_num in range(1, 100001):
            file_size_kb = file_num  # 파일 크기는 1 ~ 100,000 KB
            file_data = 'X' * (file_size_kb * 1024)  # 파일 크기만큼 가상 데이터 생성 (1KB = 1024바이트)
            virtual_files[file_num] = file_data  # 파일 데이터 저장
    print(f"총 {len(virtual_files)}개의 가상 파일 생성 완료!")


def send_next_file_num(conn):#캐시가 받아야할 다음 파일 정보를 알려주기 위함
    while FLAG:
        # 값이 0보다 큰 것들 중 가장 작은 짝수 index 찾기
        if cache_servers[0][2] == conn:
            for i in range(Max[0], len(data_array), 2):  # 짝수 index만 순회
                if data_array[i] > 0:
                    next_min[0] = i
                    # next_min 값을 짝수 cache로 전달
                    conn.sendall(f"NEXT:{next_min[0]}\n".encode())
                    break
        # 값이 0보다 큰 것들 중 가장 작은 홀수 index 찾기
        else:
            for i in range(Max[1], len(data_array), 2):  # 홀수 index만 순회
                if data_array[i] > 0:
                    next_min[1] = i
                    # next_min 값을 홀수 cache로 전달
                    conn.sendall(f"NEXT:{next_min[1]}\n".encode())
                    break
    

def identify_connection(conn):
    # cache_servers 리스트에서 conn이 있는지 확인
    for cache_server in cache_servers:
        if cache_server[2] == conn:  # cache_servers에서 conn과 비교
            print("이 연결은 캐시 서버입니다.")
            return "cache_server"
    
    # client_conns 리스트에서 conn이 있는지 확인
    for client_conn in client_conns:
        if client_conn[0] == conn:  # client_conns에서 conn과 비교
            print("이 연결은 클라이언트입니다.")
            return "client"
    
    # 리스트에서 찾을 수 없는 경우
    print("이 연결은 캐시 서버나 클라이언트가 아닙니다.")
    return "unknown"

# 파일 전송 시간 계산 및 전송 처리 함수
def send_file(conn, file_num, file_size_kb, speed_kbps):
    
    #캐시, 클라이언트에 따라 data_array 업데이트 하기
    node=identify_connection(conn)

    if node=="client":
        processed_file-=-1
        data_array[file_num]-=1
    else:
        processed_file-=data_array[file_num]
        data_array[file_num]=0
    
    # 가상 파일 데이터 가져오기
    file_data = virtual_files[file_num]  # 이미 생성된 가상 파일 데이터 가져옴

    #파일 요청 횟수 생성
    request_cnt=data_array[file_num]

    #max_file_num 생성 및 Max값 업데이트
    if(file_num%2==0):
        max_file_num=Max[0]
        Max[0]=file_num
    else:
        max_file_num=Max[1]
        Max[1]=file_num
    # 헤더 메시지 생성
    header_message = f"FILE:{file_num}"
    
    #tail 메시지 생성
    tail_message=f"{max_file_num}:{request_cnt}"

    # 헤더와 파일 데이터를 결합한 전체 메시지에 \n 추가
    full_message = header_message + file_data + tail_message+"\n"  # 전체 메시지에 \n 추가

    transfer_time = file_size_kb / speed_kbps  # 전송에 필요한 시간 계산
    print(f"파일 전송 시작: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 예상 소요 시간 {transfer_time:.2f}초")

    time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 전체 메시지를 청크 단위로 전송
    total_bytes = len(full_message)
    sent_bytes = 0

    while sent_bytes < total_bytes:
        chunk_size = min(4096, total_bytes - sent_bytes)  # 한 번에 보낼 청크 크기 계산
        chunk = full_message[sent_bytes:sent_bytes + chunk_size].encode()  # 청크 데이터 추출 및 인코딩
        conn.sendall(chunk)  # 청크 전송
        sent_bytes += chunk_size

    print(f"파일 전송 완료: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 실제 소요 시간 {transfer_time:.2f}초")

    if processed_file<=0:
        if all(value == 0 for value in data_array):
            FLAG=0
            send_flag_to_all()

def set_cache(): #홀짝캐시에게 25MB만큼의 데이터 전송하기
    total_mb_sent_even = 0  # 짝수 캐시에게 보낸 총 데이터 크기 (MB)
    total_mb_sent_odd = 0   # 홀수 캐시에게 보낸 총 데이터 크기 (MB)

    # 짝수 캐시와 홀수 캐시의 conn 구분
    even_cache_conn = cache_servers[0][2]  # 짝수 캐시의 conn
    odd_cache_conn = cache_servers[1][2]   # 홀수 캐시의 conn

    # 짝수 인덱스부터 시작해서 캐시로 파일 보내기
    for file_num in range(2, len(data_array), 2):  # 짝수 파일 번호만 순회
        if data_array[file_num] > 0:
            file_size_kb = file_num  # 파일 번호가 곧 크기(KB 단위)
            file_size_mb = file_size_kb / 1024  # MB 단위로 변환

            if total_mb_sent_even + file_size_mb <= 25:  # 25MB를 넘지 않도록
                # send_file 함수를 사용하여 짝수 캐시에 파일 전송
                send_file(even_cache_conn, file_num, file_size_kb, DATA_TO_CACHE_SPEED)
                total_mb_sent_even += file_size_mb  # 전송한 데이터 크기 업데이트          
                
            else:
                break  # 25MB를 넘으면 중단

    # 홀수 인덱스부터 시작해서 캐시로 파일 보내기
    for file_num in range(1, len(data_array), 2):  # 홀수 파일 번호만 순회
        if data_array[file_num] > 0:
            file_size_kb = file_num  # 파일 번호가 곧 크기(KB 단위)
            file_size_mb = file_size_kb / 1024  # MB 단위로 변환

            if total_mb_sent_odd + file_size_mb <= 25:  # 25MB를 넘지 않도록
                # send_file 함수를 사용하여 짝수 캐시에 파일 전송
                send_file(odd_cache_conn, file_num, file_size_kb, DATA_TO_CACHE_SPEED)
                total_mb_sent_odd += file_size_mb  # 전송한 데이터 크기 업데이트          
                
            else:
                break  # 25MB를 넘으면 중단

    print("캐시 서버로 25MB 이내의 파일을 전송 완료했습니다.")

def request_processing(conn, addr): 
    global data_array  # 전역 변수를 함수 내에서 사용하기 위해 선언

    print(f"연결된 {addr}로부터 파일 요청 처리 시작")

    buffer = ""  # 받은 데이터를 일시적으로 저장할 버퍼

    while FLAG:
        try:
            # 4096 바이트 단위로 데이터 수신
            data_chunk = conn.recv(4096).decode()
            if not data_chunk:
                break  # 연결이 종료되면 루프 탈출

            buffer += data_chunk  # 버퍼에 받은 데이터 추가

            # '\n'이 메시지의 끝을 의미하므로, 이를 기준으로 메시지 분리
            while '\n' in buffer:
                # '\n'을 기준으로 메시지를 분리
                message, buffer = buffer.split('\n', 1)

                # 요청 메시지 형식 구분: REQUEST로 시작하는 파일 요청
                if message.startswith("REQUEST:"):
                    _, file_num_str = message.split(":")  # "REQUEST:file_num" 형식
                    file_num = int(file_num_str)
                    print(f"데이터 서버: {addr}로부터 {file_num}번 파일 요청 수신")

                    # 요청한 파일의 크기 계산 및 전송 처리
                    with virtual_files_lock:
                        if file_num in virtual_files:
                            file_size_kb = len(virtual_files[file_num]) // 1024  # 파일 크기(KB) 계산
                            print(f"데이터 서버: {file_num}번 파일을 전송 준비 중 (크기: {file_size_kb} KB)")

                            # send_file 함수를 사용하여 파일 전송
                            send_file(conn,file_num, file_size_kb, DATA_TO_CLIENT_SPEED)

                        else:
                            print(f"데이터 서버: {file_num}번 파일을 찾을 수 없음")
                            #conn.sendall(f"파일을 찾을 수 없습니다: {file_num}".encode())

                # RANDOM:random_list 메시지 처리
                elif message.startswith("RANDOM:"):
                    _, random_list_str = message.split(":", 1)  # "RANDOM:random_list" 형식
                    random_list = random_list_str.split(",")  # 쉼표로 구분된 random_list 받기
                    random_list = [int(num) for num in random_list]  # 파일 번호 목록을 정수로 변환
                    print(f"데이터 서버: {addr}로부터 랜덤 파일 목록 수신: {random_list[:10]}... (총 {len(random_list)}개 파일)")

                    # random_list를 참고하여 data_array 업데이트
                    for file_num in random_list:
                        data_array[file_num] += 1  # 파일 번호에 해당하는 요청 횟수 증가
                        processed_file+=1
                    
                    if processed_file==4000:
                        set_cache()
                        send_flag_to_all()
                        
                else:
                    print(f"잘못된 요청 형식 수신: {message}")
                    #conn.sendall("잘못된 요청입니다.".encode())
                    continue

        except ValueError:
            print(f"잘못된 파일 번호 수신: {data_chunk}")
            #conn.sendall("잘못된 요청입니다.".encode())
            continue

    conn.close()

# 캐시 서버 연결 처리 함수
def handle_cache_server(conn, addr):
    print(f"연결된 캐시 서버: {addr}")
    port = conn.recv(1024).decode()  # 캐시 서버의 포트 번호를 받음
    cache_servers.append((addr[0], port, conn))  # 캐시 서버 정보 저장
    
    # 캐시 서버에 대한 추가 처리 가능

    
def send_flag_to_all():
    # 모든 캐시 서버에 FLAG 메시지 전송
    for cache_server in cache_servers:
        cache_server[2].sendall(f"FLAG:{FLAG}\n".encode())  # cache_server[2]는 conn 객체

    if(FLAG==1):
        # 모든 클라이언트에 FLAG 메시지 전송
        for client_conn in client_conns:
            client_conn[0].sendall(f"FLAG:{FLAG}\n".encode())  # client_conn[0]는 conn 객체
        
    print(f"모든 캐시 서버와 클라이언트에게 FLAG:{FLAG} 메시지를 전송했습니다.")


def start_server():
    #파일 생성
    create_virtual_files()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    # 데이터 서버 실행 중이라는 메시지 출력
    print(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")

    # 먼저 캐시 서버 2개와 연결
    print("캐시 서버와 연결 중...")
    for i in range(2):  # 캐시 서버 2개 연결
        conn, addr = server.accept()
        print(f"캐시 서버 {i + 1} 연결 완료: {addr}")
        thread = threading.Thread(target=handle_cache_server, args=(conn, addr))
        thread.start()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1나중에 handle_cache를 수정하고 나서 스레드 한번 더 생각해보자
        thread = threading.Thread(target=request_processing, args=(conn, addr))
        thread.start()

    # 캐시 서버와 연결 후 클라이언트와 연결
    print("클라이언트 연결 대기 중...")


    # 4개의 클라이언트가 모두 연결될 때까지 대기
    while len(client_conns) < MAX_CLIENTS:
        conn, addr = server.accept()
        client_conns.append((conn, addr))
        print(f"클라이언트 연결 완료: {addr}")

        # 클라이언트에게 캐시 서버 정보를 전송
        conn.sendall(f"{cache_servers[0]}:{cache_servers[1]}".encode())

    # 4개의 클라이언트가 연결된 후에 요청 처리 시작
    print(f"모든 클라이언트가 연결됨. 파일 전송 시작.")
    for conn, addr in client_conns:
        thread = threading.Thread(target=request_processing, args=(conn, addr))
        thread.start()



if __name__ == "__main__":
    start_server()


