const timerTemplate = document.getElementById("rest-timer-template");
const workoutList = document.getElementById("workout-list");
let restTimerId = null;
let activeTimerPanel = null;
let visibilityHandler = null;

function formatDuration(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function isExerciseComplete(exerciseBlock) {
  return Array.from(exerciseBlock.querySelectorAll("[data-line-form]")).every((row) =>
    row.classList.contains("done")
  );
}

function moveExerciseToBottomWhenComplete(exerciseBlock) {
  if (workoutList && exerciseBlock && isExerciseComplete(exerciseBlock)) {
    workoutList.appendChild(exerciseBlock);
  }
}

// afterElement : la ligne de série qui vient d'être validée
function startRestTimer(seconds, label, exerciseBlock, afterElement) {
  // Nettoyage du timer précédent
  if (restTimerId) {
    window.clearInterval(restTimerId);
    restTimerId = null;
  }
  if (activeTimerPanel) {
    activeTimerPanel.remove();
    activeTimerPanel = null;
  }
  if (visibilityHandler) {
    document.removeEventListener("visibilitychange", visibilityHandler);
    visibilityHandler = null;
  }

  if (!exerciseBlock) return;
  if (!seconds) {
    moveExerciseToBottomWhenComplete(exerciseBlock);
    return;
  }

  const timerPanel = timerTemplate.content.firstElementChild.cloneNode(true);
  const timerLabel = timerPanel.querySelector("[data-rest-timer-label]");
  const timerValue = timerPanel.querySelector("[data-rest-timer-value]");

  // Heure de fin absolue — résistant aux pauses et dérives de setInterval
  const endTime = Date.now() + seconds * 1000;

  activeTimerPanel = timerPanel;
  timerPanel.classList.remove("finished");
  timerLabel.textContent = label;
  timerValue.textContent = formatDuration(seconds);

  // Positionnement : juste après la série validée, pas en haut du bloc
  if (afterElement) {
    afterElement.insertAdjacentElement("afterend", timerPanel);
  } else {
    const seriesList = exerciseBlock.querySelector(".series-list");
    exerciseBlock.insertBefore(timerPanel, seriesList);
  }

  // Scroll minimal — juste assez pour rendre le timer visible
  timerPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  function tick() {
    const remaining = Math.ceil((endTime - Date.now()) / 1000);
    if (remaining <= 0) {
      window.clearInterval(restTimerId);
      restTimerId = null;
      document.removeEventListener("visibilitychange", visibilityHandler);
      visibilityHandler = null;
      timerValue.textContent = "00:00";
      timerLabel.textContent = `${label} - repos termine`;
      timerPanel.classList.add("finished");
      moveExerciseToBottomWhenComplete(exerciseBlock);
      return;
    }
    timerValue.textContent = formatDuration(remaining);
  }

  restTimerId = window.setInterval(tick, 1000);

  // Resync immédiat quand l'écran se réveille (téléphone, onglet)
  visibilityHandler = () => {
    if (!document.hidden) tick();
  };
  document.addEventListener("visibilitychange", visibilityHandler);
}

document.querySelectorAll("[data-line-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    const status = form.querySelector(".line-status");
    const inputs = form.querySelectorAll("input");
    button.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: {"Accept": "application/json"},
      });
      if (!response.ok) throw new Error("save failed");
      const data = await response.json();
      if (data.ok) {
        const exerciseBlock = form.closest("[data-exercise-block]");
        form.classList.add("done");
        status.textContent = `Validee ${data.completed_at}`;
        inputs.forEach((input) => {
          input.disabled = true;
          input.classList.add("locked");
        });
        button.textContent = "Validee";
        const label = `${data.exercise_name} ${data.serie_label}`;
        // On passe form pour positionner le timer juste en dessous
        startRestTimer(data.rest_seconds, label, exerciseBlock, form);
      }
    } catch (error) {
      status.textContent = "Erreur";
      form.classList.add("error");
      button.disabled = false;
    }
  });
});

document.querySelectorAll("[data-order-form]").forEach((form) => {
  const input = form.querySelector("input[name='ordre']");
  let submitted = false;

  input.addEventListener("change", () => {
    if (submitted) return;
    submitted = true;
    form.requestSubmit();
  });
});
