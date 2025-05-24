const socket = io();

// 메시지 받기
socket.on("receive_message", ({ username, message }) => {
  const ul = document.querySelector(".chat-msg-list");
  const li = document.createElement("li");
  li.textContent = `${username}: ${message}`;
  ul.appendChild(li);
});

// 메시지 보내기
const form = document.getElementById("message_form");
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const input = form.querySelector("input[name='message']");
  const msg = input.value.trim();
  if (!msg) return;

  socket.emit("message", {
    username: "guest", // 나중에 사용자 이름 받을 수 있음
    message: msg
  });

  input.value = "";
});
