// 게임 상태 불러오기 함수
async function fetchGameState() {
  try {
    const response = await fetch("/api/game/state");
    if (!response.ok) throw new Error("네트워크 오류");

    const data = await response.json();
    console.log("[게임 상태]", data);

    updateGameStateUI(data);
  } catch (error) {
    console.error("게임 상태 불러오기 실패:", error);
  }
}

// 게임 상태를 화면에 표시하는 함수
function updateGameStateUI(state) {
  const currentWordEl = document.getElementById("current-word");
  const turnPlayerEl = document.getElementById("turn-player");
  const wordHistoryEl = document.getElementById("word-history");

  currentWordEl.textContent = state.current_word || "(없음)";
  turnPlayerEl.textContent = state.turn_player || "(대기 중)";
  
  // 단어 기록을 갱신
  wordHistoryEl.innerHTML = "";  // 초기화
  state.word_history.forEach((word) => {
    const li = document.createElement("li");
    li.textContent = word;
    wordHistoryEl.appendChild(li);
  });
}

// 페이지 로드 시 게임 상태 불러오기
document.addEventListener("DOMContentLoaded", () => {
  fetchGameState();
});
