from socket import*
import threading

serverName = '222.109.225.78'
serverPort = 12000
my_turn = False
game_over = False

def receive_messages(clientSocket):
    global my_turn, game_over
    while True:
        try:
            modifiedSentence = clientSocket.recv(1024)
            if not modifiedSentence:
                print("서버 연결 끊김")
                game_over = True
                break
            
            server_said = modifiedSentence.decode()
#            if server_said == "TURN":
#                my_turn = True
#                print("Player의 차례")
#            else:
            print(f"\n[서버]: {server_said}")
            my_turn = True          #추가
#            game_over = True

        except:
            print("서버 통신 오류")
            game_over = True
            break




def main():
    global my_turn, game_over

    clientSocket = socket(AF_INET, SOCK_STREAM)
    try:
        clientSocket.connect((serverName, serverPort))
        print(f"서버 {serverName}:{serverPort}에 연결됨")
    except Exception as e:
        print(f"서버 연결 실패: {e}")
        return
    

    threading.Thread(target=receive_messages, args=(clientSocket,), daemon=True).start()

    try:
        while not game_over:
            if my_turn:
                sentence = input().strip()
                if sentence == '0':
                    clientSocket.send("GiveUp".encode())
                    game_over = True
                elif sentence:
                    try:
                        clientSocket.send(sentence.encode())
                        my_turn = False
                    except:
                        print("서버에 단어 전송 실패")
    except:
        print("\n 게임 종료")
    


    clientSocket.close()
    print("끝말잇기 종료")
    
if __name__ == "__main__":
    main()