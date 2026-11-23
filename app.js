(() => {
  const tg = window.Telegram?.WebApp;
  const consent = document.getElementById("consent");
  const code = document.getElementById("accessCode");
  const unlock = document.getElementById("unlock");
  const hint = document.getElementById("lockHint");
  const survey = document.getElementById("survey");
  const result = document.getElementById("result");
  const progressText = document.getElementById("progressText");
  const progressBar = document.getElementById("progressBar");
  let unlocked = false;

  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#120b10");
    tg.setBackgroundColor("#120b10");
  }

  // Discourage casual copying. This cannot prevent screenshots or OS-level capture.
  document.addEventListener("contextmenu", e => e.preventDefault());
  document.addEventListener("copy", e => e.preventDefault());
  document.addEventListener("cut", e => e.preventDefault());
  document.addEventListener("selectstart", e => {
    if (!e.target.matches("input,textarea")) e.preventDefault();
  });
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && ["c","x","s","p","u"].includes(e.key.toLowerCase())) {
      e.preventDefault();
    }
  });

  unlock.addEventListener("click", () => {
    if (!consent.checked) {
      hint.textContent = "Сначала подтверди согласие на отправку ответов.";
      return;
    }
    if (!code.value.trim()) {
      hint.textContent = "Введи защитный код.";
      return;
    }
    unlocked = true;
    survey.classList.remove("hidden");
    hint.textContent = "Доступ открыт. Можешь заполнить анкету.";
    unlock.disabled = true;
    code.disabled = true;
    document.querySelector(".lock").classList.add("unlocked");
    survey.scrollIntoView({behavior:"smooth", block:"start"});
  });

  function updateProgress() {
    let count = 0;
    for (let i=1;i<=11;i++) {
      if (survey.querySelector(`[name="q${i}"]:checked`)) count++;
    }
    if (survey.querySelector('[name="q12"]').value.trim()) count++;
    progressText.textContent = `${count} / 12`;
    progressBar.style.width = `${count/12*100}%`;
  }
  survey.addEventListener("change", updateProgress);
  survey.addEventListener("input", updateProgress);

  survey.addEventListener("submit", async e => {
    e.preventDefault();
    if (!unlocked) return;
    const initData = tg?.initData || "";
    if (!initData) {
      alert("Открой анкету через Telegram-бота, а не в обычном браузере.");
      return;
    }

    const answers = {};
    for (let i=1;i<=11;i++) {
      const selected = survey.querySelector(`[name="q${i}"]:checked`);
      if (!selected) {
        alert(`Пожалуйста, ответь на вопрос №${i}.`);
        survey.querySelector(`[data-q="q${i}"]`).scrollIntoView({behavior:"smooth"});
        return;
      }
      answers[`q${i}`] = selected.value;
    }
    answers.q12 = survey.querySelector('[name="q12"]').value.trim();

    const submitButton = survey.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "Отправляем…";

    try {
      const response = await fetch("/api/submit", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          init_data:initData,
          access_code:code.value,
          answers
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Не удалось отправить ответы");
      survey.classList.add("hidden");
      result.classList.remove("hidden");
      result.innerHTML = "<h2>Спасибо! ✦</h2><p>Твои ответы отправлены. Хорошего дня!</p>";
      tg?.HapticFeedback?.notificationOccurred("success");
      tg?.BackButton?.hide();
    } catch (err) {
      alert(err.message);
      submitButton.disabled = false;
      submitButton.textContent = "Отправить ответы";
    }
  });
})();
