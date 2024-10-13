1조 조원 구성 및 역할

20203043 권수현 - client 코드 작성, 디버깅, 서버 알고리즘 구상, Readme 작성

20203058 남태인 - 전체 코드 점검, data server 코드 작성, 디버깅, 서버 알고리즘 구상, Readme 작성

20203072 안민호 – cache server 코드 작성, 디버깅, 서버 알고리즘 구상, Readme 작성



1. 프로그램 구성요소 : data.py, cache.py, client.py

◆ data.py 구성요소

① start_server()
- create_virtual_file()로 1~10,000까지의 가상 파일 생성
- 데이터 서버 소켓 생성
- 캐시 서버 2개와 연결, 캐시 서버 정보(ip, 포트 번호) 저장 / request_processing()를 thread로 시작
- 클라이언트 4개와 연결, 캐시 서버 정보를 클라이언트로 전송 / request_processing()를 thread로 시작

②request_processing(conn,addr)
-cache와 client로 부터 들어오는 message 수신 receive_data()
-message 종류: REQUEST, RANDOM
-REQUEST: 요청 받은 file_num을 cache 혹은 client로 전송
-RANDOM: client로 부터 random list 처리/random list 수신 완료시 set_cache() 및 send_flag_to_all() 실행

③set_cache(): cache에게 25MB 만큼의 파일을 전송

④send_flag_to_all(): cache와 client에게 파일 요청을 시작하라는 flag 신호 전송

⑤send_file: 메시지의 헤더와(ex: FILE:file_num,file_data) 파일 데이터를 전송/모든 파일 송수신 완료 시 종료 FLAG 전송


◆ cache.py 구성요소

① start_cache_server()
- cache_lock을 사용하여 캐시를 안전하게 관리할 수 있도록 쓰레드간 동기화
- connect_to_data_server() 함수 호출하여 데이터 서버와 연결 시도
- 캐시 서버 소켓 설정 및 바인딩 후 데이터 서버에 포트 번호 전송
- request_from_data_server() 함수가 별도의 스레드로 실행되어 캐시 서버가 데이터 서버로부터 파일을 받아오는 작업 관리
- 캐시 서버는 클라이언트 연결이 발생할 때마다 handle_client()함수가 새로운 스레드로 실행

② connect_to_data_server(host, port)
- 데이터 서버에 연결을 설정하는 함수
- 데이터 서버와 통신할 소켓을 생성하고 주어진 host, port로 연결 시도

③ request_from_data_server()
- 데이터 서버로부터 초기 파일을 받아와 캐시에 저장
- FLAG == 0 상태에서 대기하다가 FLAG == 1 메시지를 수신하면 동작
- 데이터 서버로부터 수신한 파일데이터를 캐시에 저장하고, 캐시 용량이 초과하는지 검사 및 Max 함수 업데이트
- 캐시 서버가 데이터 서버에 파일 데이터를 요청할 조건(남은 공간이 데이터 서버에서 넘겨줄 파일보다 클 때)이 만족하면 데이터 서버로부터 파일 요청

④ receive_data(socket)
- 데이터 서버에서 FILE과 FLAG 데이터를 수신하는 함수
- 클라이언트에서 REQUEST(파일 요청) 데이터를 수신하는 함수
- 수신된 데이터를 버퍼에 저장하고, 메시지의 끝이 '\n'(줄바꿈)처리 되어 있으면 메시지를 분리하여 반환

⑤ handle_client(conn, addr)
- 클라이언트 요청(REQUEST) 처리 함수
- 클라이언트로부터 파일 요청을 받고, 요청한 파일이 캐시에 존재하는 경우 파일을 찾아 전송(캐시 히트), 없을 경우 데이터 서버에 파일을 요청하도록 함(캐시 미스)

⑥ send_file(conn, file_num, file_data, request_cnt, max_file_num)
- 클라이언트에게 파일을 전송하는 함수
- 파일 데이터를 클라이언트로 전송하기 위한 메시지(FILE) 생성 및 파일 전송
- 파일 전송 후, request_cnt(파일 요청 수(중복 수))를 감소(-1)시키고, 0인 경우, 캐시에서 해당 파일을 제거

⑦ close_data_server_connection()
- 데이터 서버와의 연결을 종료하는 함수

◆ client.py 구성요소

① start_client()
- 데이터 서버 연결 및 데이터 서버에서 2개의 캐시 정보 수신. 이후 2개의 캐시 서버와 연결
- random_list() : 1~100,000 범위 중 1000개의 랜덤 리스트 생성
- send_random_list : "RANDOM:{random_list}\n"로 랜덤 리스트를 데이터 서버에 전송
- 데이터 서버로부터 "FLAG:1\n" 메시지를 받으면 랜덤 리스트를 기반으로 파일 요청 시작(request_file())

② request_file()
- 홀수 번호 파일인 경우 첫 번째 캐시 서버, 짝수 번호 파일인 경우 두 번째 캐시 서버로 요청
- 모든 캐시 서버에서 캐시 미스가 발생하면 데이터 서버에 요청

③. request_cache() 
- "REQUEST:{file_num}\n" 메시지로 캐시 서버에 파일 요청
- 캐시 서버로부터 Cache Hit 수신 시 receive_file()로 받은 file_data를 virtual_storage()에 저장
- Cache Miss 발생 시 request_file()함수에 False 반환

④. request_data_server()
- "REQUEST:{file_num}\n" 메시지로 데이터 서버에 파일 요청
- receive_file()로 받은 data를 virtual_storage()에 저장


2. 소스코드 컴파일 방법 (GCP 사용)

① 구글 클라우드에 접속하여 VM instance를 생성한다.
	지역 : us-central1로 설정
	머신 유형 : e2-micro
	부팅 디스크 : Debian

② 방화벽 규칙을 추가한다
	대상 : 모든 인스턴스 선택
	소스 IP 범위 : 0.0.0.0/0  (모든 IP 주소 허용)
	프로토콜 및 포트 : TCP와 해당 포트를 지정 (port : 9999)

③ 생성된 인스턴스의 SSH를 실행한다.

④ Python과 개발 도구의 패키지들을 설치한다 (Debian 기준)
	sudo apt update
	sudo apt install python3
	sudo apt install python3-pip
	pip install numpy
	pip install numpy scipy
	pip install loguru //Python에서 로그(logging)기능을 제공하는 라이브러리

⑤ 가상환경을 생성하고 활성화한다.
	python3 -m venv myenv(가상환경 이름)
	source myenv/bin/activate //가상환경 활성화

⑥ UPLOAD FILE을 클릭하여 server.py를 업로드한다.
	server.py가 업로드된 디렉터리에서 python3 server.py로 Data server를 실행한다.

⑦ 로컬에서 powershell 터미널 6개를 열어 터미널 2개는 python3 cache.py로 캐시 서버를 실행시키고, 나머지 터미널 4개는 python3 client.py로 client를 실행한다.
	
⑧ 2개의 Cache server와 4개의 client가 모두 연결되면 프로그램이 실행된다.

3. 규칙 및 알고리즘 설명

⦁ 알고리즘 시나리오

### 클라이언트 초기 설정

각각의 클라이언트가 요청할 랜덤 파일 리스트를 생성 후, 정렬

정렬된 리스트를 데이터 서버에 전송,

### 데이터 서버 초기 설정

데이터 서버는 1x10000 리스트 만든다

데이터 서버 리스트(data_array)

- 데이터 서버의 파일 요청 개수(=파일 다운 횟수) 행렬에 업데이트 (3개면 0 → 3)
- 데이터 서버→ 캐시로 파일 보낸 경우, 해당 파일의 파일 요청 개수는 0으로 업데이트
- 데이터 서버→클라이언트로 파일 보낸 경우, 해당 파일의 요청 개수는 -1

### 캐시 서버 초기 설정

캐시 서버는 데이터 서버로 부터 25MB 만큼의 초기 파일을 수신한다

### 데이터 서버 →캐시에 파일 전송

데이터 서버가 캐시에 파일 번호, 파일 데이터, 다음 요청 할 파일, 파일별 다운 횟수 전송(크기가 작은 파일부터 우선적으로 보냄)

- 캐시는 홀수 파일 캐시와 짝수 파일 캐시로 이루어져있음

### 클라이언트 → 캐시 서버에 파일 요청

클라이언트는 캐시에게 파일을 요청함(작은 파일을 우선적으로 요청)

캐시에 클라이언트가 요청한 파일이 존재하는 경우, 클라이언트에게 cache hit 메시지와  전송하고 파일 요청 횟수를 1 줄인다.

- 파일 요청 횟수가 0이되면 캐시에서 제거된다

캐시에 클라이언트가 요청한 파일이 존재하지 않는 경우, 클라이언트에 “Cache Miss” 메시지를 보낸다

- 캐시에 요청 파일이 존재하지 않는 경우 클라이언트는 데이터 서버에게 파일을 요청
- 데이터 서버는 클라이언트가 직접 파일을 요청한 경우, 해당 파일 요청 개수를 1 줄인다

### 캐시—>데이터 서버에 파일 요청(캐시 업데이트)

1. 데이터 서버가 cache에 파일 데이터를 보낼 때, 캐시가 다음 요청 해야할 파일의 정보를 전송한다.
2. 캐시는 Max에 이 값을 저장하고, 빈 공간이 Max보다 크면 Max에 해당하는 파일을 데이터 서버에 요청한다.

### 클라이언트 → 데이터 서버 파일 요청(큰 파일)

클라이언트는 캐시에 파일을 요청할 때 크기가 작은 파일 여러개와 큰 파일 하나를 요청한다.

초기 캐시 서버에는 큰 파일이 없을 가능성이 높으므로 캐시 서버는 큰 파일을 높은 확률로 거절한다.

그러면 클라이언트는 큰 파일을 데이터 서버에게 직접 요청한다

### 프로그램 종료 과정

데이터 서버 행렬의 모든 값이 0이 되고 모든 클라이언트가 다운 완료가 파일의 개수가 각각 1000개인 경우, 데이터 서버에서 종료 flag를 cache에 전송한다.

cache는 client로 부터 다운 완료 신호와 데이터 서버로 부터 종료 flag를 받은 경우 종료된다. -미구현-

각각의 client는 1000개의 파일이 다운되면 종료된다.

### 메시지 형식(’\n’으로 구분)

- FLAG:1 (설명: 데이터 서버의 파일 준비가 끝나면 다른 cache와 client에게 시작하라고 보내는 신호,0은 종료 신호)
- FILE:file_num:file_data:max_file_num:request_cnt    (설명 파일 데이터 전송 시 , FILE: 파일 번호 : 파일 데이터:캐시에 보내지는 파일 중 가장 크기가 큰 파일 번호:파일 요청 횟수)
- REQUEST:file_num (설명: 파일 요청 메시지 , REQUEST: 파일 번호)
- RANDOM:client에서 data server에 요청할 random 1000개 파일 목록
    
    ㄴRANDOM:random_list
    
- Cache Hit/ Cache Miss

4. Error or Additional Message Handling
▶ Additional Message Handling

⊙ Data Server
① 메시지 관리
	- FLAG:1 (데이터 서버의 파일 준비가 끝나면 다른 cache와 client에게 시작하라고 보내는 신호)
	- FILE:file_num:file_data:max_file_num:request_cnt(파일 데이터 전송 시 , FILE: 파일 번호 : 파일 데이터:캐시가 요청 해야할 파일 번호:파일 요청 횟수)
	- REQUEST:file_num (파일 요청 메시지 , REQUEST: 파일 번호)
	- RANDOM:(client에서 data server에 요청할 random 1000개 파일 목록,RANDOM:random_list)

⊙ Cache Server
① 메시지 관리
	- message 형태 : FILE(파일 전송), FLAG(동작 제어), REQUEST(파일 요청)
2. 사용 부분
 	- request_from_data_server()
   		message.startswith("FILE:"): 데이터 서버 수신 파일 데이터 처리
   		message.startswith("FLAG:"): 데이터 서버가 지휘하는 FLAG값에 따라 동작 제어 (FLAG:0 종료 / FLAG:1실행)
 	 -  handle_client()
  		 message.startswith("REQUEST:"): 클라이언트로부터 파일 요청 수신 처리
	- receive_data()
  	 	줄바꿈('\n')을 기준으로 메시지를 분리하고 처리

⊙ Client
① FLAG:1 메시지 수신 후 파일 요청 시작:
	 - FLAG:1 메시지를 수신한 후에 파일 요청을 시작하도록 구현
	- 만약 FLAG:1 메시지가 도착하지 않으면 파일요청 작업이 시작되지 X
	- flag_msg를 검사하고 요청을 시작하기 때문에 메시지가 올바른 형식이 아닌 경우 예외 처리

② 캐시 서버와 데이터 서버의 응답 메시지 처리:
	- 캐시 서버에 요청 후 수신된 응답이 "Cache Hit" 또는 "Cache Miss" 경우로 나눠서 처리
	- Cache Hit 시에는 파일 수신, Cache Miss 시에는 데이터 서버로 요청하는 방식으로 메시지 처리
	
③ FILE: 메시지 수신으로 파일 구분:
	- 파일 데이터임을 확인하는 부분 (receive_file 함수)를 추가하여 FILE: 메시지로 담겨오는 파일 데이터를 '\n'를 기준으로 처리
		


▶ Error Handling (Exception 처리 포함)

⊙ Data Server
① 소켓 관련 오류: 클라이언트 또는 캐시 서버와의 연결이 끊어지거나, 소켓에서 데이터를 수신하거나 전송할 때 발생하는 오류를 처리하기 위해 예외 처리를 사용.
② 값 변환 오류: 주로 문자열을 정수로 변환하는 부분에서 발생할 수 있는 ValueError를 처리.

⊙ Cache Server
① connect_to_data_server() (try-except)
   	- 데이터 서버 연결 중 오류 처리
② receive_data() (try-except)
   	- 소켓으로부터 데이터를 수신할 때 발생할 수 있는 모든 예외 처리
③ message.starstwith("FILE:") (try-except)
   	- 데이터 서버에서 파일 수신할 때 발생하는 예외 처리
④ except ValueERROR as e
   	- 캐시 서버에서 파일 저장할 때 발생하는 오류 처리
⑤ 데이터 서버에서 파일 요청 및 수신 중 오류 처리 (try-except)

⊙ Client
① 연결 실패 또는 통신 오류
	- 데이터 서버 연결 오류: data_server_conn.connect((DATA_SERVER_HOST, DATA_SERVER_PORT))에서 데이터 서버에 연결하는 동안 발생하는 예외는 try-except로 처리
	- 캐시 서버 연결 오류: 캐시 서버에 각각 연결할 때도 try-except 구문을 사용하여 오류 발생 시 예외처리
	- 파일 수신 중 예외 처리: 캐시 서버나 데이터 서버에서 파일을 수신하는 도중 오류가 발생할 경우 (request_cache, request_data_server 함수), 예외 메시지 출력 

② 소켓 연결 종료 처리(Graceful Termination)
	- 모든 파일 요청이 완료된 후 캐시 서버와 데이터 서버와의 연결을 안전하게 종료하기 위해 cache_conn.close()와 data_server_conn.close()를 사용하여 종료

5. Additional Comments (팀플 날짜 기록)
2024/10/05
과제 시작
데이터서버, 캐시 서버, 클라이언트 간 연결 방식 고민 (해결)
1. 데이터 서버에 먼저 캐시 서버 1,2가 연결하면서 포트번호를 등록한다
2. 클라이언트도 데이터 서버에 연결하면서, 등록된 캐시서버 1,2의 포트번호를 요청한다
3. 클라이언트는 데이터 서버로부터 받은 포트번호를 사용해 캐시 서버에 연결한다.

2024/10/06
소켓 연결

2024/10/07
알고리즘 구상

2024/10/09 ~ 2024/10/11
임무 분담 및 알고리즘 구현

2024/10/12 ~ 2024/10/14
코드 무한 디버깅 및 수정
readme 작성, 발표영상 제작