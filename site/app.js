const filters = [...document.querySelectorAll("[data-filter]")];
const projects = [...document.querySelectorAll("[data-category]")];
const count = document.querySelector("#visible-count");
const year = document.querySelector("#year");

function selectFilter(category) {
  filters.forEach((button) => {
    const active = button.dataset.filter === category;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  let visible = 0;
  projects.forEach((project) => {
    const matches = category === "all" || project.dataset.category === category;
    project.hidden = !matches;
    if (matches) visible += 1;
  });

  if (count) count.textContent = String(visible);
}

filters.forEach((button) => {
  button.addEventListener("click", () => selectFilter(button.dataset.filter));
});

if (year) year.textContent = String(new Date().getFullYear());
