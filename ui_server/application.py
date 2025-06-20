from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import os
import smtplib
from email.message import EmailMessage
import re
from scapy.sendrecv import sr1
from scapy.layers.inet import IP, ICMP

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# SMTP 서버 설정
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'eunhakdev@gmail.com'
SMTP_PASSWORD = 'ozuchisccifxnkto'

# 게임 상태 관리
game_state = {
    'players': [],  # 플레이어 소켓ID 목록
    'nicknames': {},  # 소켓ID: 닉네임 매핑
    'emails': {},  # 소켓ID: 이메일 매핑
    'network_info': {},  # 소켓ID: {ip, rtt} 매핑
    'current_turn': None,  # 현재 턴 (소켓ID)
    'last_word': '',  # 마지막으로 제출된 단어
    'used_words': [],  # 단어 기록 (입력 순서 유지, 중복 체크)
    'game_started': False  # 게임 시작 여부
}


# 이메일 전송 함수
def send_game_result_email(to_email, result, details):
    msg = EmailMessage()
    msg.set_content(
        f"끝말잇기 게임 결과\n\n"
        f"📝 결과: {result}\n"
        f"✏️ 마지막 단어: {details.get('last_word', '')}\n"
        f"🧬 상대 플레이어: {details.get('opponent', '알 수 없음')}\n"
        f"🗃️ 단어 기록: {', '.join(details.get('word_history', []))}\n"
        f"\n✨플레이해 주셔서 감사합니다!✨"
    )
    msg['Subject'] = f'끝말잇기 게임 결과 - {result}'
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True, "결과가 이메일로 전송되었습니다."
    except Exception as e:
        print(f"이메일 전송 실패: {e}")
        return False, f"이메일 전송 실패: {str(e)}"


# ICMP Ping 전송 함수
def send_icmp_ping(target_ip, timeout=2):
    try:
        packet = IP(dst=target_ip) / ICMP()
        response = sr1(packet, timeout=timeout, verbose=False)
        if response:
            rtt = (response.time - packet.sent_time) * 1000  # ms 단위
            return True, rtt
        return False, None
    except Exception as e:
        print(f"ICMP 전송 오류: {e}")
        return False, None


# 기본 라우트 - 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')


# 게임 페이지 라우트
@app.route('/game')
def game():
    return render_template('game.html')


# 정적 파일 서빙 (CSS, JS 등)
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


# 소켓 연결 이벤트
@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f'클라이언트 연결됨: {sid}')

    client_ip = request.remote_addr
    success, rtt = send_icmp_ping(client_ip)
    if success and rtt is not None:
        game_state['network_info'][sid] = {'ip': client_ip, 'rtt': rtt}
        emit('message', {
            'type': 'system',
            'text': f'네트워크 정보: IP={client_ip}, RTT={rtt:.2f}ms'
        }, room=sid)
    else:
        game_state['network_info'][sid] = {'ip': client_ip, 'rtt': None}
        emit('message', {
            'type': 'system',
            'text': f'네트워크 정보: IP={client_ip}, RTT 측정 실패'
        })

    if len(game_state['players']) >= 2 and game_state['game_started']:
        emit('message', {'type': 'error', 'message': '이미 게임이 진행 중입니다.'})
        return

    emit('message', {'type': 'system', 'text': '서버에 연결되었습니다.'})


# 소켓 연결 해제 이벤트
@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f'클라이언트 연결 끊김: {sid}')

    if sid in game_state['players']:
        nickname = game_state['nicknames'].get(sid, '알 수 없음')
        to_email = game_state['emails'].get(sid)
        opponent_sid = next((p for p in game_state['players'] if p != sid), None)
        opponent_nickname = game_state['nicknames'].get(opponent_sid, '알 수 없음') if opponent_sid else '알 수 없음'

        game_state['players'].remove(sid)
        if sid in game_state['nicknames']:
            del game_state['nicknames'][sid]
        if sid in game_state['emails']:
            del game_state['emails'][sid]
        if sid in game_state['network_info']:
            del game_state['network_info'][sid]

        if game_state['game_started'] and len(game_state['players']) > 0:
            remaining_player = game_state['players'][0]
            emit('message', {
                'type': 'victory',
                'reason': f'{nickname}님이 게임을 나갔습니다.'
            }, room=opponent_sid)

            # 이메일 전송: 패배자
            if to_email:
                success, email_message = send_game_result_email(
                    to_email,
                    "패배",
                    {
                        'last_word': game_state['last_word'],
                        'opponent': opponent_nickname,
                        'word_history': game_state['used_words']  # list 사용
                    }
                )
                emit('message', {
                    'type': 'email_status',
                    'message': email_message
                }, room=sid)

            # 이메일 전송: 승리자
            if opponent_sid and game_state['emails'].get(opponent_sid):
                success, email_message = send_game_result_email(
                    game_state['emails'][opponent_sid],
                    "승리",
                    {
                        'last_word': game_state['last_word'],
                        'opponent': nickname,
                        'word_history': game_state['used_words']  # list 사용
                    }
                )
                emit('message', {
                    'type': 'email_status',
                    'message': email_message
                }, room=opponent_sid)

        if len(game_state['players']) < 2:
            game_state['game_started'] = False
            game_state['current_turn'] = None
            game_state['last_word'] = ''
            game_state['used_words'] = []  # 초기화 시 빈 리스트


# 게임 참가 이벤트
@socketio.on('join')
def on_join(data):
    sid = request.sid
    nickname = data.get('nickname', '플레이어')
    email = data.get('email', '')

    # 이메일 형식 검증
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not email or not re.match(email_regex, email):
        emit('message', {'type': 'error', 'message': '유효한 이메일 주소를 입력해주세요.'})
        return

    if game_state['game_started']:
        emit('message', {'type': 'error', 'message': '이미 게임이 진행 중입니다.'})
        return

    if len(game_state['players']) >= 2:
        emit('message', {'type': 'error', 'message': '이미 두 명의 플레이어가 있습니다.'})
        return

    # 플레이어 정보 저장
    game_state['players'].append(sid)
    game_state['nicknames'][sid] = nickname
    game_state['emails'][sid] = email

    emit('message', {'type': 'system', 'text': f'{nickname}님이 게임에 참가했습니다.'}, broadcast=True)

    if len(game_state['players']) == 2:
        start_game()


# 단어 제출 이벤트
@socketio.on('word')
def on_word(word):
    sid = request.sid
    word = word.strip()

    if not game_state['game_started']:
        emit('message', {'type': 'error', 'message': '게임이 시작되지 않았습니다.'})
        return

    if sid not in game_state['players']:
        emit('message', {'type': 'error', 'message': '게임 참가자가 아닙니다.'})
        return

    if game_state['current_turn'] != sid:
        emit('message', {'type': 'error', 'message': '당신의 차례가 아닙니다.'})
        return

    # "GiveUp" 메시지 처리 (기권)
    if word == "GiveUp":
        handle_surrender(sid)
        return

    # 끝말잇기 규칙 검사
    if game_state['last_word']:
        last_char = game_state['last_word'][-1]
        first_char = word[0] if word else ''

        if last_char != first_char:
            emit('message', {
                'type': 'invalid',
                'reason': f"'{last_char}'(으)로 시작하는 단어를 입력해야 합니다."
            })
            return

    # 중복 단어 체크 후 추가
    if word not in game_state['used_words']:  # 중복 방지
        game_state['used_words'].append(word)

    game_state['last_word'] = word

    nickname = game_state['nicknames'].get(sid, '알 수 없음')

    # 모든 플레이어에게 단어 전송
    emit('message', {
        'type': 'word',
        'nickname': nickname,
        'word': word
    }, broadcast=True)

    # 턴 변경
    next_player = get_next_player(sid)
    game_state['current_turn'] = next_player

    # 다음 플레이어에게 턴 알림
    emit('message', {'type': 'turn'}, room=next_player)


# 기권 이벤트
@socketio.on('surrender')
def on_surrender():
    handle_surrender(request.sid)


# 게임 시작 함수
def start_game():
    if len(game_state['players']) != 2:
        return

    game_state['game_started'] = True
    game_state['used_words'] = []  # 게임 시작 시 빈 리스트로 초기화

    # 무작위로 시작 플레이어 선택
    first_player = random.choice(game_state['players'])
    game_state['current_turn'] = first_player

    # 시작 단어 선택 (첫 플레이어가 자유롭게 선택)
    game_state['last_word'] = ''

    # 각 플레이어에게 게임 시작 알림
    first_player_nickname = game_state['nicknames'].get(first_player, '알 수 없음')

    # 모든 플레이어에게 게임 시작 및 첫 플레이어 알림
    for player in game_state['players']:
        emit('message', {
            'type': 'start',
            'firstPlayer': first_player_nickname,
            'startWord': ''
        }, room=player)

    # 첫 번째 플레이어에게 턴 부여
    emit('message', {'type': 'turn'}, room=first_player)


# 다음 플레이어 찾기
def get_next_player(current_player):
    players = game_state['players']
    if len(players) <= 1:
        return current_player

    # 현재 플레이어 이외의 플레이어 선택
    for player in players:
        if player != current_player:
            return player

    return current_player


# 기권 처리 함수
def handle_surrender(sid):
    if not game_state['game_started'] or sid not in game_state['players']:
        return

    nickname = game_state['nicknames'].get(sid, '알 수 없음')
    to_email = game_state['emails'].get(sid)

    # 다른 플레이어 찾기
    other_player = None
    for player in game_state['players']:
        if player != sid:
            other_player = player
            break

    if other_player:
        # 승리 메시지 전송
        emit('message', {
            'type': 'victory',
            'reason': f'{nickname}님이 기권했습니다.'
        }, room=other_player)

        # 이메일 전송: 승리자
        if game_state['emails'].get(other_player):
            success, email_message = send_game_result_email(
                game_state['emails'][other_player],
                "승리",
                {
                    'last_word': game_state['last_word'],
                    'opponent': nickname,
                    'word_history': game_state['used_words']  # list 사용
                }
            )
            emit('message', {
                'type': 'email_status',
                'message': email_message
            }, room=other_player)

    # 이메일 전송: 패배자
    if to_email:
        success, email_message = send_game_result_email(
            to_email,
            "패배",
            {
                'last_word': game_state['last_word'],
                'opponent': game_state['nicknames'].get(other_player, '알 수 없음'),
                'word_history': game_state['used_words']  # list 사용
            }
        )
        emit('message', {
            'type': 'email_status',
            'message': email_message
        }, room=sid)

    emit('message', {
        'type': 'defeat',
        'reason': '기권하셨습니다.'
    }, room=sid)

    game_state['game_started'] = False
    game_state['current_turn'] = None
    game_state['last_word'] = ''
    game_state['used_words'] = []  # 초기화 시 빈 리스트


# 서버 시작
if __name__ == '__main__':
    # 'templates' 디렉토리가 없으면 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')

    # 'static/css' 디렉토리가 없으면 생성
    if not os.path.exists('static/css'):
        os.makedirs('static/css')

    print('서버 시작: 12000번 포트에서 실행 중…')
    socketio.run(app, host='0.0.0.0', port=12000, debug=True)