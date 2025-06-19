from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import os
from scapy.sendrecv import sr1
from scapy.layers.inet import IP, ICMP

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# 게임 상태 관리
game_state = {
    'players': [],  # 플레이어 소켓ID 목록
    'nicknames': {},  # 소켓ID: 닉네임 매핑
    'network_info': {},  # 소켓ID: {ip, rtt} 매핑
    'current_turn': None,  # 현재 턴 (소켓ID)
    'last_word': '',  # 마지막으로 제출된 단어
    'used_words': set(),  # 사용된 단어 집합
    'game_started': False  # 게임 시작 여부
}


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
    # ping
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
        game_state['players'].remove(sid)
        if sid in game_state['nicknames']:
            del game_state['nicknames'][sid]
        if sid in game_state['network_info']:
            del game_state['network_info'][sid]

        if game_state['game_started'] and len(game_state['players']) > 0:
            remaining_player = game_state['players'][0]
            emit('message', {
                'type': 'victory',
                'reason': f'{nickname}님이 게임을 나갔습니다.'
            }, room=remaining_player)

        if len(game_state['players']) < 2:
            game_state['game_started'] = False
            game_state['current_turn'] = None
            game_state['last_word'] = ''
            game_state['used_words'] = set()


# 게임 참가 이벤트
@socketio.on('join')
def on_join(data):
    sid = request.sid
    nickname = data.get('nickname', '플레이어')

    if game_state['game_started']:
        emit('message', {'type': 'error', 'message': '이미 게임이 진행 중입니다.'})
        return

    if len(game_state['players']) >= 2:
        emit('message', {'type': 'error', 'message': '이미 두 명의 플레이어가 있습니다.'})
        return

    game_state['players'].append(sid)
    game_state['nicknames'][sid] = nickname

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

    if word == "GiveUp":
        handle_surrender(sid)
        return

    if game_state['last_word']:
        last_char = game_state['last_word'][-1]
        first_char = word[0] if word else ''

        if last_char != first_char:
            emit('message', {
                'type': 'invalid',
                'reason': f"'{last_char}'(으)로 시작하는 단어를 입력해야 합니다."
            })
            return

    if word in game_state['used_words']:
        emit('message', {
            'type': 'invalid',
            'reason': '이미 사용된 단어입니다.'
        })
        return

    game_state['last_word'] = word
    game_state['used_words'].add(word)

    nickname = game_state['nicknames'].get(sid, '알 수 없음')

    emit('message', {
        'type': 'word',
        'nickname': nickname,
        'word': word
    }, broadcast=True)

    next_player = get_next_player(sid)
    game_state['current_turn'] = next_player

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
    game_state['used_words'] = set()

    first_player = random.choice(game_state['players'])
    game_state['current_turn'] = first_player

    game_state['last_word'] = ''

    first_player_nickname = game_state['nicknames'].get(first_player, '알 수 없음')

    for player in game_state['players']:
        emit('message', {
            'type': 'start',
            'firstPlayer': first_player_nickname,
            'startWord': ''
        }, room=player)

    emit('message', {'type': 'turn'}, room=first_player)


# 다음 플레이어 찾기
def get_next_player(current_player):
    players = game_state['players']
    if len(players) <= 1:
        return current_player

    for player in players:
        if player != current_player:
            return player

    return current_player


# 기권 처리 함수
def handle_surrender(sid):
    if not game_state['game_started'] or sid not in game_state['players']:
        return

    nickname = game_state['nicknames'].get(sid, '알 수 없음')

    other_player = None
    for player in game_state['players']:
        if player != sid:
            other_player = player
            break

    if other_player:
        emit('message', {
            'type': 'victory',
            'reason': f'{nickname}님이 기권했습니다.'
        }, room=other_player)

    emit('message', {
        'type': 'defeat',
        'reason': '기권하셨습니다.'
    }, room=sid)

    game_state['game_started'] = False
    game_state['current_turn'] = None
    game_state['last_word'] = ''
    game_state['used_words'] = set()


# 서버 시작
if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')

    if not os.path.exists('static/css'):
        os.makedirs('static/css')

    print('서버 시작: 12000번 포트에서 실행 중...')
    socketio.run(app, host='0.0.0.0', port=12000, debug=True)