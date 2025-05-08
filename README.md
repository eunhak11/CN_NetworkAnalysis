## 🗃️ 프로젝트 소개
✈️*항공대 컴퓨터 네트워크 과목 텀 프로젝트*✈️

**5-Layer Internet Protocol**의 패킷 분석을 위한 끝말잇기 게임 서버 구축

##### 프로젝트 기간: 25.04.28~25.05.26

<br>

## 📚 기술 스택

 <img src="https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white"> <img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white"> <img src="https://img.shields.io/badge/html5-E34F26?style=for-the-badge&logo=html5&logoColor=white"> 
  <img src="https://img.shields.io/badge/css-1572B6?style=for-the-badge&logo=css3&logoColor=white"> 
  <img src="https://img.shields.io/badge/javascript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">

<img src="https://img.shields.io/badge/git-F05032?style=for-the-badge&logo=git&logoColor=white"> <img src="https://img.shields.io/badge/github-181717?style=for-the-badge&logo=github&logoColor=white"> <img src="https://img.shields.io/badge/wireshark-1679A7?style=for-the-badge&logo=socket.io&logoColor=#1679A7">

<br><br>

## 😎 팀원 소개


|💪 조재현 💪| 🏎️ 이석진 🏎️ | ⚡ 이은학 ⚡ |
| --- | --- | --- |
| 프론트 | 백(서버) | PM,  백(서버) |
| 막내 | 둘째 | 첫째 |
| [Github : cjh30808](https://github.com/cjh030808) | [Github : DLseokJin](https://github.com/DlSeokJin) | [Github : eunhak11](https://github.com/eunhak11) |

<u>***최차봉의 아이들 Let's Go***</u>

 <br><br>

## 💻 서버 및 동작 개요
본 프로젝트는 Python을 활용한 실시간 끝말잇기 게임을 구현하며, TCP 서버, TCP 클라이언트, Flask 서버로 구성된다.

Wireshark를 이용한 패킷 분석을 통해 네트워크 프로토콜의 동작 원리를 학습하고, 컴퓨터 네트워크 과목에서 배운 개념들을 실제 통신 과정에 접목시켜 이해 및 활용 능력을 기르는 것을 목표로 한다.

#### 주요 동작

🎲 TCP 서버

- 끝말잇기 게임의 핵심 로직을 담당한다.
- 게임 시작 시 랜덤한 단어 제공
- 플레이어의 단어 제출을 받아 끝말 연결 여부, 중복 단어 사용 여부를 검증.
- 턴 당 10초의 시간 제한을 관리하며, 시간 초과 시 탈락 처리



🎲 TCP 클라이언트

- 사용자 입력을 간단한 콘솔 인터페이스로 처리
- 오고 가는 단어 확인
- 통신 안정성 확인


🎲 Flask 서버

- HTTP 기반 웹 인터페이스를 제공해 게임 진행 상황을 표시한다.
- 현재 단어, 플레이어 순서, 남은 시간 등을 웹 페이지에 표시.
- 쿠키를 활용해 세션을 관리.
- 캐싱으로 정적 콘텐츠 전송을 최소화 하여 로딩 속도를 최적화한다.

🎲 패킷 분석

Wireshark를 사용해 TCP 패킷의 연결 설정(3-way handshake), 데이터 전송, 종료 과정과 HTTP 패킷의 요청/응답 구조, 쿠키 및 캐시 동작 등을 분석한다.


프로젝트 진행 과정에서 직접 설계할 수 있는 Application과 Transport Layer의 패킷들을 우선적으로 분석하고 , 나머지 Layer에 대한 분석도 추후에 진행한다.
