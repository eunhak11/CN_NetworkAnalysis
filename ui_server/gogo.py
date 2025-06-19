from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import time
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# 게임 상태 관리
game_state = {
    'players': [],  # 플레이어 소켓ID 목록
    'nicknames': {},  # 소켓ID: 닉네임 매핑
    'current_turn': None,  # 현재 턴 (소켓ID)
    'last_word': '',  # 마지막으로 제출된 단어
    'used_words': set(),  # 사용된 단어 집합
    'game_started': False  # 게임 시작 여부
}

# 기본 라우트 - 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 정적 파일 서빙 (CSS, JS 등)
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# 소켓 연결 이벤트
@socketio.on('connect')
def on_connect():
    sid = request.sid
    app.logger.info(f'클라이언트 연결됨: {sid}')
    
    # 이미 두 명이 접속해 있고 게임이 시작된 경우, 새로운 연결 거부
    if len(game_state['players']) >= 2 and game_state['game_started']:
        emit('message', {'type': 'error', 'message': '이미 게임이 진행 중입니다.'})
        return
    
    emit('message', {'type': 'system', 'text': '서버에 연결되었습니다.'})

# 소켓 연결 해제 이벤트
@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    app.logger.info(f'클라이언트 연결 끊김: {sid}')
    
    # 게임 중이던 플레이어가 나간 경우
    if sid in game_state['players']:
        nickname = game_state['nicknames'].get(sid, '알 수 없음')
        game_state['players'].remove(sid)
        
        if sid in game_state['nicknames']:
            del game_state['nicknames'][sid]
        
        # 게임이 시작된 상태에서 플레이어가 나간 경우
        if game_state['game_started'] and len(game_state['players']) > 0:
            # 남은 플레이어에게 승리 메시지 전송
            remaining_player = game_state['players'][0]
            emit('message', {
                'type': 'victory', 
                'reason': f'{nickname}님이 게임을 나갔습니다.'
            }, room=remaining_player)
        
        # 게임 상태 초기화
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
    
    # 이미 게임이 시작된 경우
    if game_state['game_started']:
        emit('message', {'type': 'error', 'message': '이미 게임이 진행 중입니다.'})
        return
    
    # 이미 두 명이 접속해 있는 경우
    if len(game_state['players']) >= 2:
        emit('message', {'type': 'error', 'message': '이미 두 명의 플레이어가 있습니다.'})
        return
    
    # 플레이어 정보 저장
    game_state['players'].append(sid)
    game_state['nicknames'][sid] = nickname
    
    emit('message', {'type': 'system', 'text': f'{nickname}님이 게임에 참가했습니다.'}, broadcast=True)
    
    # 두 명이 모이면 게임 시작
    if len(game_state['players']) == 2:
        start_game()

# 단어 제출 이벤트
@socketio.on('word')
def on_word(word):
    sid = request.sid
    word = word.strip()
    
    # 게임이 시작되지 않은 경우
    if not game_state['game_started']:
        emit('message', {'type': 'error', 'message': '게임이 시작되지 않았습니다.'})
        return
    
    # 플레이어가 아닌 경우
    if sid not in game_state['players']:
        emit('message', {'type': 'error', 'message': '게임 참가자가 아닙니다.'})
        return
    
    # 턴이 아닌 경우
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
    
    # 이미 사용된 단어 검사
    if word in game_state['used_words']:
        emit('message', {
            'type': 'invalid',
            'reason': '이미 사용된 단어입니다.'
        })
        return
    
    # 유효한 단어 처리
    game_state['last_word'] = word
    game_state['used_words'].add(word)
    
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
    game_state['used_words'] = set()
    
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
    
    return current_player  # 예상치 못한 상황

# 기권 처리 함수
def handle_surrender(sid):
    if not game_state['game_started'] or sid not in game_state['players']:
        return
    
    nickname = game_state['nicknames'].get(sid, '알 수 없음')
    
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
    
    # 패배 메시지 전송
    emit('message', {
        'type': 'defeat',
        'reason': '기권하셨습니다.'
    }, room=sid)
    
    # 게임 초기화
    game_state['game_started'] = False
    game_state['current_turn'] = None
    game_state['last_word'] = ''
    game_state['used_words'] = set()

# 서버 시작
if __name__ == '__main__':
    # 'templates' 디렉토리가 없으면 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 'static/css' 디렉토리가 없으면 생성
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    
    app.logger.info('서버 시작: 12000번 포트에서 실행 중...')
    socketio.run(app, host='0.0.0.0', port=12000, debug=True)