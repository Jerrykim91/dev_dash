"use strict";
const form = document.getElementById("login-form");
const password = document.getElementById("password");
const toggle = document.getElementById("toggle-password");
toggle.addEventListener("click", () => {
  const show = password.type === "password";
  password.type = show ? "text" : "password";
  toggle.textContent = show ? "숨김" : "표시";
  toggle.setAttribute("aria-label", show ? "비밀번호 숨기기" : "비밀번호 표시");
  toggle.setAttribute("aria-pressed", String(show));
});
form.addEventListener("submit", (event) => {
  event.preventDefault();
  password.value = "";
  document.getElementById("login-status").textContent = "로그인은 아직 준비 중이에요. ‘로그인 없이 둘러보기’로 작업 공간에 들어가세요.";
});
