1조 조원 구성 및 역할

20203043 권수현 - 

20203058 남태인 - 

20203072 안민호 – 



1. 프로그램 구성요소 : server.py, cache.py, client.py

◆ server.py 구성요소

- 


◆ cache.py 구성요소

-

◆ client.py 구성요소

-


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

3. 작업 분배 및 부하 분산에 사용한 알고리즘 설명

⦁ 장점 : 

⦁ 단점 : 


4. Error or Additional Message Handling

▶ Error Handling (Exception 처리 포함)
⊙ Data Server
	- 

	▷ 예외 처리가 적용된 메서드 : 
	⦁ 
		- 

	⦁ 
		- 


⊙ Cache Server

	▷ 예외 처리가 적용된 메서드 : 
	  ⦁ 

		- 
		☆ 기대 효과: 

⊙ Client

	▷ 예외 처리가 적용된 메서드 : 
	  ⦁ 

		- 
		☆ 기대 효과: 


▶ Additional Message Handling


5. Additional Comments (팀플 날짜 기록)

2024-10-05
과제 시작
데이터서버, 캐시 서버, 클라이언트 간 연결 방식 고민 (해결)
1. 데이터 서버에 먼저 캐시 서버 1,2가 연결하면서 포트번호를 등록한다
2. 클라이언트도 데이터 서버에 연결하면서, 등록된 캐시서버 1,2의 포트번호를 요청한다
3. 클라이언트는 데이터 서버로부터 받은 포트번호를 사용해 캐시 서버에 연결한다.