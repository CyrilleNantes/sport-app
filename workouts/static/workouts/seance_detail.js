const timerTemplate = document.getElementById("rest-timer-template");
const workoutList = document.getElementById("workout-list");
let restTimerId = null;
let activeTimerPanel = null;

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

function startRestTimer(seconds, label, exerciseBlock) {
  if (restTimerId) {
    window.clearInterval(restTimerId);
  }
  if (activeTimerPanel) {
    activeTimerPanel.remove();
  }
  if (!exerciseBlock) {
    return;
  }
  if (!seconds) {
    moveExerciseToBottomWhenComplete(exerciseBlock);
    return;
  }

  const timerPanel = timerTemplate.content.firstElementChild.cloneNode(true);
  const timerLabel = timerPanel.querySelector("[data-rest-timer-label]");
  const timerValue = timerPanel.querySelector("[data-rest-timer-value]");
  const seriesList = exerciseBlock.querySelector(".series-list");
  let remaining = seconds;
  activeTimerPanel = timerPanel;
  timerPanel.classList.remove("finished");
  timerLabel.textContent = label;
  timerValue.textContent = formatDuration(remaining);
  exerciseBlock.insertBefore(timerPanel, seriesList);
  timerPanel.scrollIntoView({behavior: "smooth", block: "center"});

  restTimerId = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      window.clearInterval(restTimerId);
      restTimerId = null;
      timerValue.textContent = "00:00";
      timerLabel.textContent = `${label} - repos termine`;
      timerPanel.classList.add("finished");
      moveExerciseToBottomWhenComplete(exerciseBlock);
      return;
    }
    timerValue.textContent = formatDuration(remaining);
  }, 1000);
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
        startRestTimer(data.rest_seconds, label, exerciseBlock);
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
    if (submitted) {
      return;
    }
    submitted = true;
    form.requestSubmit();
  });
});
