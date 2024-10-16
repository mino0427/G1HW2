import socket
import threading
import time
import logging

log_file = "data.txt"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)

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
processed_file=0
buffer=''#버퍼 역할을 함


virtual_files_lock = threading.Lock()

def create_virtual_files():
    global virtual_files
    print("가상 파일 크기 정보 생성 시작...")
    logging.debug("가상 파일 크기 정보 생성 시작...")
#    with virtual_files_lock:
    for file_num in range(1, 10001):
        file_size_kb = file_num  # 파일 크기는 1 ~ 100,000 KB
        virtual_files[file_num] = file_size_kb  # 파일 크기만 저장 (KB 단위)
    print(f"총 {len(virtual_files)}개의 가상 파일 크기 정보 생성 완료!")
    logging.debug(f"총 {len(virtual_files)}개의 가상 파일 크기 정보 생성 완료!")


def find_next_file_num(conn):#캐시가 받아야할 다음 파일 정보를 알려주기 위함
    global data_array
    global FLAG
    global Max
    global cache_servers
    

    
    while FLAG:
        # 값이 0보다 큰 것들 중 가장 작은 짝수 index 찾기
        if cache_servers[0][2] == conn:
            for i in range(Max[0], len(data_array), 2):  # 짝수 index만 순회
                if data_array[i] > 0:
                    
                    return i
        # 값이 0보다 큰 것들 중 가장 작은 홀수 index 찾기
        else:
            for i in range(Max[1], len(data_array), 2):  # 홀수 index만 순회
                if data_array[i] > 0:
                    
                    # next_min 값을 홀수 cache로 전달
                    return i
    

def identify_connection(conn):
    global cache_servers
    

    
    # cache_servers 리스트에서 conn이 있는지 확인
    for cache_server in cache_servers:
        if cache_server[2] == conn:  # cache_servers에서 conn과 비교

            return "cache_server"
    
    # client_conns 리스트에서 conn이 있는지 확인
    for client_conn in client_conns:
        if client_conn[0] == conn:  # client_conns에서 conn과 비교

            return "client"
    
    # 리스트에서 찾을 수 없는 경우
    print("이 연결은 캐시 서버나 클라이언트가 아닙니다.")
    logging.debug("이 연결은 캐시 서버나 클라이언트가 아닙니다.")
    return "unknown"

# 파일 전송 시간 계산 및 전송 처리 함수
def send_file(conn, file_num, file_size_kb, speed_kbps):
    global processed_file
    global data_array
    global Max

    
    # 캐시, 클라이언트에 따라 data_array 업데이트 하기
    node = identify_connection(conn)

    # 파일 요청 횟수 생성
    request_cnt = data_array[file_num]

    # max_file_num 생성 및 Max값 업데이트
    if file_num % 2 == 0:
        next_file_num = find_next_file_num(conn)
        Max[0] = file_num

    else:
        next_file_num =find_next_file_num(conn)
        Max[1] = file_num
  


    # 헤더 메시지 생성
    header_message = f"FILE:{file_num}:".encode()

    # tail 메시지 생성
    tail_message = f":{next_file_num}:{request_cnt}\n".encode()

    # 전체 전송 크기 계산
    total_bytes = file_size_kb * 1024 // 8  # 가상 파일의 크기를 바이트로 변환

    transfer_time = file_size_kb / speed_kbps  # 전송에 필요한 시간 계산
    print(f"파일 전송 시작: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 예상 소요 시간 {transfer_time:.2f}초")
    logging.debug(f"파일 전송 시작: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 예상 소요 시간 {transfer_time:.2f}초")

    #time.sleep(transfer_time)  # 전송 시간 동안 대기

    # 전체 메시지 생성 (헤더 + 파일 데이터 + tail 메시지)
    file_data = b'X' * total_bytes  # 'X'를 바이트로 변환
    full_message = header_message + file_data + tail_message  # 모든 부분을 바이트로 결합


    # full_message를 청크 단위로 전송
    sent_bytes = 0
    while sent_bytes < len(full_message):
        chunk_size = min(4096, len(full_message) - sent_bytes)  # 한 번에 보낼 청크 크기 계산
        chunk = full_message[sent_bytes:sent_bytes + chunk_size]  # 청크 데이터 추출
        conn.sendall(chunk)  # 청크 전송
        sent_bytes += chunk_size


    #data_array 업데이트
 #   with virtual_files_lock:    
    if node == "client":
        processed_file += 1
        data_array[file_num] -= 1
    else:
        processed_file -= data_array[file_num]
        data_array[file_num] = 0

    print(f"파일 전송 완료: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 실제 소요 시간 {transfer_time:.2f}초")
    logging.debug(f"파일 전송 완료: 파일 번호 {file_num}, 크기 {file_size_kb} KB, 실제 소요 시간 {transfer_time:.2f}초")

    # 모든 파일이 처리되었는지 확인 후 종료 처리
    if processed_file <= 0:
        if all(value == 0 for value in data_array):
            FLAG = 0
            send_flag_to_all()


def set_cache(): #홀짝캐시에게 25MB만큼의 데이터 전송하기
    global data_array
    global cache_servers
    global DATA_TO_CACHE_SPEED
    global DATA_TO_CLIENT_SPEED
    
    total_mb_sent_even = 0  # 짝수 캐시에게 보낸 총 데이터 크기 (MB)
    total_mb_sent_odd = 0   # 홀수 캐시에게 보낸 총 데이터 크기 (MB)

    # 짝수 캐시와 홀수 캐시의 conn 구분
    even_cache_conn = cache_servers[1][2]  # 짝수 캐시의 conn
    odd_cache_conn = cache_servers[0][2]   # 홀수 캐시의 conn

    even_flag=0#0이면 짝수 캐시 완료되면 1
    odd_flag=0#0이면 홀수 캐시 완료되면 1

    # 짝수와 홀수 인덱스를 같은 루프에서 처리
    for file_num in range(len(data_array)):
        if data_array[file_num] > 0:
            file_size_kb = file_num  # 파일 번호가 곧 크기(KB 단위)
            file_size_mb = file_size_kb / 1024  # MB 단위로 변환

            if file_num % 2 == 0:  # 짝수 파일 처리
                if total_mb_sent_even + file_size_mb <= 25:  # 25MB를 넘지 않도록
                    # send_file 함수를 사용하여 짝수 캐시에 파일 전송
                    send_file(even_cache_conn, file_num, file_size_kb, DATA_TO_CACHE_SPEED)
                    total_mb_sent_even += file_size_mb  # 전송한 데이터 크기 업데이트
                else:
                    even_flag=1
                    if(even_flag==1 and odd_flag==1):
                        break
                    continue  # 짝수 캐시 초기 세팅이 끝나면 홀수 파일 처리로 넘어감
            else:  # 홀수 파일 처리
                if total_mb_sent_odd + file_size_mb <= 25:  # 25MB를 넘지 않도록
                    # send_file 함수를 사용하여 홀수 캐시에 파일 전송
                    send_file(odd_cache_conn, file_num, file_size_kb, DATA_TO_CACHE_SPEED)
                    total_mb_sent_odd += file_size_mb  # 전송한 데이터 크기 업데이트
                else:
                    odd=1
                    if(even_flag==1 and odd_flag==1):
                        break
                    continue  # 홀수 캐시 초기 세팅이 끝나면 짝수 파일 처리로 넘어감


    print("홀짝 캐시 서버로 25MB 이내의 파일을 전송 완료했습니다.")
    logging.debug("홀짝 캐시 서버로 25MB 이내의 파일을 전송 완료했습니다.")

# 데이터를 청크 단위로 받는 함수
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



def request_processing(conn, addr): 
    global data_array  # 전역 변수를 함수 내에서 사용하기 위해 선언
    global processed_file
    global FLAG
    global virtual_files
    global DATA_TO_CLIENT_SPEED
    
    print(f"연결된 {addr}로부터 파일 요청 처리 시작")
    logging.debug(f"연결된 {addr}로부터 파일 요청 처리 시작")

    while FLAG:
        try:
            # 데이터를 청크 단위로 수신
            message = receive_data(conn)
           

            # '\n'이 메시지의 끝을 의미하므로 이를 기준으로 메시지 처리
            
            # 요청 메시지 형식 구분: REQUEST로 시작하는 파일 요청
            if not message:
                continue
            
            elif message.startswith("REQUEST:"):
                _, file_num_str = message.split(":")  # "REQUEST:file_num" 형식
                file_num = int(file_num_str)
                print(f"데이터 서버: {addr}로부터 {file_num}번 파일 요청 수신")
                logging.debug(f"데이터 서버: {addr}로부터 {file_num}번 파일 요청 수신")

                # 요청한 파일의 크기 계산 및 전송 처리
                #with virtual_files_lock:
                if file_num in virtual_files:
                    file_size_kb = file_num  # 파일 크기(KB) 계산
                    print(f"데이터 서버: {file_num}번 파일을 전송 준비 중 (크기: {file_size_kb} KB)")
                    logging.debug(f"데이터 서버: {file_num}번 파일을 전송 준비 중 (크기: {file_size_kb} KB)")

                    # send_file 함수를 사용하여 파일 전송
                    send_file(conn, file_num, file_size_kb, DATA_TO_CLIENT_SPEED)

                else:
                    print(f"데이터 서버: {file_num}번 파일을 찾을 수 없음")
                    logging.debug(f"데이터 서버: {file_num}번 파일을 찾을 수 없음")
                    continue
                    #conn.sendall(f"파일을 찾을 수 없습니다: {file_num}".encode())

            # RANDOM:random_list 메시지 처리
            elif message.startswith("RANDOM:"):
                _, random_list_str = message.split(":", 1)  # "RANDOM:random_list" 형식
                random_list = random_list_str.split(":")  # 쉼표로 구분된 random_list 받기
                random_list = [int(num) for num in random_list]  # 파일 번호 목록을 정수로 변환
                #logging.debug(f"데이터 서버: {addr}로부터 랜덤 파일 목록 수신: {random_list[:10]}... (총 {len(random_list)}개 파일)")

                # random_list를 참고하여 data_array 업데이트
                for file_num in random_list:
                    data_array[file_num] += 1  # 파일 번호에 해당하는 요청 횟수 증가
                    processed_file += 1

                
                if processed_file == 400:
                    set_cache()
                    send_flag_to_all()

             
                    
            else:
                print(f"잘못된 요청 형식 수신: {message}")
                logging.debug(f"잘못된 요청 형식 수신: {message}")
                continue

        except ValueError:
            print(f"잘못된 파일 번호 수신: {_}")
            logging.debug(f"잘못된 파일 번호 수신: {_}")
            continue

    conn.close()


# # 캐시 서버 연결 처리 함수
# def handle_cache_server(conn, addr):
#     print(f"연결된 캐시 서버: {addr}")
#     port =int(conn.recv(1024).decode())  # 캐시 서버의 포트 번호를 받음
    
#     cache_servers.append((addr[0], port, conn))  # 캐시 서버 정보 저장
#     print(cache_servers)
#     # 캐시 서버에 대한 추가 처리 가능?????????????????????????여기 뭐 넣는 거였지?????????????????????????????????????

    
def send_flag_to_all():
    global FLAG
    global cache_servers
    
    # 모든 캐시 서버에 FLAG 메시지 전송
    for cache_server in cache_servers:
        cache_server[2].sendall(f"FLAG:{FLAG}\n".encode())  # cache_server[2]는 conn 객체
    
    
    if(FLAG==1):
        # 모든 클라이언트에 FLAG 메시지 전송
        for client_conn in client_conns:
            client_conn[0].sendall(f"FLAG:{FLAG}\n".encode())  # client_conn[0]는 conn 객체
        
    print(f"모든 캐시 서버와 클라이언트에게 FLAG:{FLAG} 메시지를 전송했습니다.")
    logging.debug(f"모든 캐시 서버와 클라이언트에게 FLAG:{FLAG} 메시지를 전송했습니다.")



def start_server():
    global cache_servers
    #파일 생성
    create_virtual_files()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    # 데이터 서버 실행 중이라는 메시지 출력
    print(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")
    logging.debug(f"Data Server가 {HOST}:{PORT}에서 실행 중입니다...")

    # 먼저 캐시 서버 2개와 연결
    print("캐시 서버와 연결 중...")
    logging.debug("캐시 서버와 연결 중...")
    for i in range(2):  # 캐시 서버 2개 연결
        conn, addr = server.accept()
        print(f"캐시 서버 {i + 1} 연결 완료: {addr}")
        logging.debug(f"캐시 서버 {i + 1} 연결 완료: {addr}")
        #thread = threading.Thread(target=handle_cache_server, args=(conn, addr))
        #thread.start()#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1나중에 handle_cache를 수정하고 나서 스레드 한번 더 생각해보자
        #     print(f"연결된 캐시 서버: {addr}")
        port =int(conn.recv(1024).decode())  # 캐시 서버의 포트 번호를 받음
        cache_servers.append((addr[0], port, conn))  # 캐시 서버 정보 저장
        print(cache_servers)
        thread = threading.Thread(target=request_processing, args=(conn, addr))
        thread.start()

    # 캐시 서버와 연결 후 클라이언트와 연결
    print("클라이언트 연결 대기 중...")
    logging.debug("클라이언트 연결 대기 중...")


    # 4개의 클라이언트가 모두 연결될 때까지 대기
    while len(client_conns) < MAX_CLIENTS:
        conn, addr = server.accept()
        client_conns.append((conn, addr))
        print(f"클라이언트 연결 완료: {addr}")
        logging.debug(f"클라이언트 연결 완료: {addr}")

        # 클라이언트에게 캐시 서버 정보를 전송
        print(cache_servers[0])
        print(cache_servers[1])
        logging.debug(cache_servers[0])
        logging.debug(cache_servers[1])
        conn.sendall(f"{cache_servers[0]}:{cache_servers[1]}".encode())

    # 4개의 클라이언트가 연결된 후에 요청 처리 시작
    print(f"모든 클라이언트가 연결됨. 파일 전송 시작.")
    logging.debug(f"모든 클라이언트가 연결됨. 파일 전송 시작.")
    for conn, addr in client_conns:
        thread = threading.Thread(target=request_processing, args=(conn, addr))
        thread.start()



if __name__ == "__main__":
    start_server()


