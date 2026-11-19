// mobile menu
const menu = document.querySelector(".menu"), nav = document.querySelector("nav");
if (menu) menu.addEventListener("click", () => {
  const o = nav.classList.toggle("open"); menu.setAttribute("aria-expanded", o);
});
// active nav link
document.querySelectorAll("nav a").forEach(a => { if (a.pathname === location.pathname) a.classList.add("active"); });
// dismissible toast, auto-hide after 6s
document.querySelectorAll(".flash").forEach(f => {
  f.querySelector("button").onclick = () => f.remove(); setTimeout(() => f.remove(), 6000);
});
// loading state on submit
document.querySelectorAll("form").forEach(f => f.addEventListener("submit", () => {
  const b = f.querySelector("button[type=submit]"); if (b && f.checkValidity()) b.classList.add("loading");
}));
// "Use my location"
const loc = document.getElementById("locate");
if (loc) loc.onclick = () => {
  if (!navigator.geolocation) return alert("Location is not supported in this browser.");
  loc.textContent = "Finding you...";
  navigator.geolocation.getCurrentPosition(p => {
    const box = document.getElementById("location");
    box.value = (box.value ? box.value + " " : "") + `(${p.coords.latitude.toFixed(5)}, ${p.coords.longitude.toFixed(5)})`;
    loc.textContent = "📍 Location added";
  }, () => { loc.textContent = "📍 Use my location"; alert("Could not get your location. Type it in instead."); });
};
// photo preview
const photo = document.getElementById("photo"), prev = document.getElementById("preview");
if (photo) photo.onchange = () => {
  const f = photo.files[0]; if (!f) return prev.style.display = "none";
  prev.src = URL.createObjectURL(f); prev.style.display = "block";
};
// incident filter chips
const chips = document.querySelectorAll(".chip[data-type]");
chips.forEach(c => c.onclick = () => {
  chips.forEach(x => x.classList.toggle("on", x === c));
  document.querySelectorAll("[data-kind]").forEach(el =>
    el.classList.toggle("hide", c.dataset.type !== "all" && el.dataset.kind !== c.dataset.type));
});
// preparedness checklist with progress (saved in this browser)
const items = document.querySelectorAll(".check input"), fill = document.getElementById("fill"), txt = document.getElementById("ptext");
if (items.length) {
  const saved = JSON.parse(localStorage.getItem("dc-check") || "[]");
  items.forEach((c, i) => { c.checked = saved.includes(i); c.onchange = update; });
  function update() {
    const done = [...items].map((c, i) => c.checked ? i : -1).filter(i => i >= 0);
    localStorage.setItem("dc-check", JSON.stringify(done));
    fill.style.width = (done.length / items.length * 100) + "%";
    txt.textContent = `${done.length} of ${items.length} ready` + (done.length === items.length ? " ✅" : "");
  }
  update();
}
