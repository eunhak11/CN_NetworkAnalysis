from socket import *
import threading

class ConnectionHandler:
    """클라이언트 연결 관리"""
    def __init__(self, game_logic):
        self.game_logic = game_logic
        self.SERVER_PORT = 12000
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind(('', self.SERVER_PORT))
        self.server_socket.listen(5)
        print(f"TCP 서버 시작: localhost:{self.SERVER_PORT}")

    def broadcast(self, message):
        """모든 클라이언트에 메시지 전송"""
        for client_id, player in self.game_logic.players.items():
            try:
                player['socket'].send(f"{message}\n".encode('utf-8'))
            except:
                pass

    def handle_client(self, client_socket, client_id):
        """클라이언트 연결 처리"""
        self.game_logic.players[client_id] = {'socket': client_socket, 'active': True}
        self.game_logic.turn_queue.append(client_id)
        client_socket.send(f"환영합니다, Player {client_id}!\n".encode('utf-8'))

        start_message = self.game_logic.start_game()
        if start_message:
            self.broadcast(start_message)

        while client_id in self.game_logic.players and self.game_logic.players[client_id]['active']:
            if self.game_logic.turn_queue and self.game_logic.turn_queue[0] == client_id:
                try:
                    client_socket.settimeout(self.game_logic.TIMEOUT)
                    self.game_logic.turn_start = time.time()
                    client_socket.send("Turn")
                    sentence = client_socket.recv(1024).decode('utf-8').strip()
                    if not sentence:
                        raise ConnectionError("클라이언트 연결 끊김")

                    valid, message = self.game_logic.validate_word(sentence, client_id)
                    self.broadcast(f"Player {client_id}: {sentence} ({message})")
                    self.game_logic.save_game_state()

                    end, end_message = self.game_logic.check_game_end()
                    if end:
                        self.broadcast(end_message)
                        break
                except socket.timeout:
                    timed_out, message = self.game_logic.check_timeout(client_id)
                    self.broadcast(f"Player {client_id} {message}")
                    self.game_logic.save_game_state()
                    end, end_message = self.game_logic.check_game_end()
                    if end:
                        self.broadcast(end_message)
                        break
                except (ConnectionError, BrokenPipeError):
                    self.game_logic.players[client_id]['active'] = False
                    self.game_logic.turn_queue.remove(client_id) if client_id in self.game_logic.turn_queue else None
                    self.broadcast(f"Player {client_id} 연결 끊김")
                    self.game_logic.save_game_state()
                    end, end_message = self.game_logic.check_game_end()
                    if end:
                        self.broadcast(end_message)
                        break

        client_socket.close()
        if client_id in self.game_logic.players:
            del self.game_logic.players[client_id]

    def run(self):
        """서버 실행"""
        client_id = 0
        while True:
            try:
                connection_socket, addr = self.server_socket.accept()
                client_id += 1
                print(f"클라이언트 연결: Player {client_id} ({addr})")
                threading.Thread(target=self.handle_client, args=(connection_socket, client_id)).start()
            except KeyboardInterrupt:
                print("서버 종료")
                break
        self.server_socket.close()