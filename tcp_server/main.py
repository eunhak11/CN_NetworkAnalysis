from game_logic import GameLogic
from connection_handler import ConnectionHandler

def main():
    """TCP 서버 실행"""
    game_logic = GameLogic()
    server = ConnectionHandler(game_logic)
    server.run()

if __name__ == '__main__':
    main()