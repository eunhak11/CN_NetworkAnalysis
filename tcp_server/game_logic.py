import random
import time
import json
import os

class GameLogic:

    """끝말잇기 게임 로직 관리"""
    def __init__(self):
        self.word_history = []  # 사용된 단어
        self.players = {}  # {client_id: {'socket': socket, 'active': bool}}
        self.turn_queue = []  # 턴 순서: [client_id]
        self.current_word = None  # 현재 단어
        self.turn_start = 0  # 턴 시작 시간
        self.TIMEOUT = 10  # 10초 제한
        # init_word.txt에서 단어 읽기
        try:
            with open('tcp_server/init_word.txt', 'r', encoding='utf-8') as f:
                self.word_list = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("Error: init_word.txt not found")
            self.word_list = ['사과', '가방']  # 기본 단어


    def start_game(self):
        """게임 시작: init_word.txt에서 랜덤 단어 선택"""
        if not self.current_word:
            self.current_word = random.choice(self.word_list)
            self.word_history.append(self.current_word)
            self.save_game_state()
            return f"게임 시작! 첫 단어: {self.current_word}"
        return None


    def validate_word(self, new_word, client_id):
        """단어 검증: 끝말 연결, 중복 여부"""
        if new_word in self.word_history:
            self.players[client_id]['active'] = False
            self.turn_queue.remove(client_id)
            return False, "중복된 단어입니다."
        if self.current_word and new_word[0] != self.current_word[-1]:
            self.players[client_id]['active'] = False
            self.turn_queue.remove(client_id)
            return False, "끝말이 연결되지 않습니다."
        self.current_word = new_word
        self.word_history.append(new_word)
        self.turn_queue.append(self.turn_queue.pop(0))  # 턴 이동
        return True, "유효한 단어입니다."


    def check_timeout(self, client_id):
        """타임아웃 확인"""
        if time.time() - self.turn_start > self.TIMEOUT:
            self.players[client_id]['active'] = False
            self.turn_queue.remove(client_id)
            return True, "시간 초과로 탈락했습니다."
        return False, ""


    def check_game_end(self):
        """게임 종료 확인"""
        active_players = [pid for pid, p in self.players.items() if p['active']]
        if len(active_players) <= 1:
            winner = active_players[0] if active_players else None
            return True, f"게임 종료! 승자: {'Player ' + str(winner) if winner else '없음'}"
        return False, ""


    def save_game_state(self):
        """게임 상태를 JSON으로 저장"""
        state = {
            'current_word': self.current_word,
            'turn_player': self.turn_queue[0] if self.turn_queue else None,
            'time_left': self.TIMEOUT - (time.time() - self.turn_start) if self.turn_queue else 0,
            'players': {pid: p['active'] for pid, p in self.players.items()},
            'word_history': self.word_history,
            'game_ended': len([p for p in self.players.values() if p['active']]) <= 1,
            'winner': next((pid for pid, p in self.players.items() if p['active']), None) if self.game_ended else None
        }
        try:
            with open('data/game_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False)
        except IOError as e:
            print(f"Error writing game_state.json: {e}")