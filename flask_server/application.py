from flask import Flask, jsonify, render_template
import json
import os

app = Flask(__name__)

# 게임 상태 파일 경로
GAME_STATE_PATH = 'data/game_state.json'

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

@app.route('/game')
def game():
    """게임 진행 UI 렌더링"""
    return render_template('game.html')

@app.route('/api/game/state', methods=['GET'])
def game_state():
    """현재 단어, 턴 플레이어, 플레이어 상태 반환"""
    try:
        with open(GAME_STATE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({
            'current_word': data['current_word'],
            'turn_player': data['turn_player'],
            'players': data['players']
        }), 200, {'Cache-Control': 'no-cache', 'Content-Type': 'application/json'}
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'Failed to read game state'}), 500

@app.route('/api/game/timer', methods=['GET'])
def game_timer():
    """턴 플레이어와 남은 시간 반환"""
    try:
        with open(GAME_STATE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({
            'turn_player': data['turn_player'],
            'time_left': data['time_left']
        }), 200, {'Cache-Control': 'no-cache', 'Content-Type': 'application/json'}
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'Failed to read timer data'}), 500

@app.route('/api/game/history', methods=['GET'])
def game_history():
    """단어 이력 반환"""
    try:
        with open(GAME_STATE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({
            'word_history': data['word_history']
        }), 200, {'Cache-Control': 'max-age=60', 'Content-Type': 'application/json'}
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'Failed to read history data'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)