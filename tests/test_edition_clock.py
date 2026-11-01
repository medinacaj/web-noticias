"""Prueba real del temporizador de la edición sin red ni dependencias nuevas."""
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node no disponible")
class EditionClockTests(unittest.TestCase):
    def test_minute_boundary_and_background_pause(self):
        script = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
let clock = Date.parse("2026-11-01T12:34:15.000Z");
let nextId = 0;
const timers = new Map();
const listeners = new Map();
class FakeDate extends Date {
  constructor(...args) { super(...(args.length ? args : [clock])); }
  static now() { return clock; }
}
function element() {
  return {
    dataset: {}, style: {}, hidden: true, disabled: false, dateTime: "",
    textContent: "", attributes: {},
    addEventListener() {},
    setAttribute(name, value) { this.attributes[name] = value; },
    matches() { return false; },
    contains() { return false; },
    focus() {},
  };
}
const ids = ["updated-at", "site-clock", "refresh-progress", "refresh-fill",
             "refresh-now", "refresh-status", "refresh-help"];
const elements = Object.fromEntries(ids.map(id => [id, element()]));
elements["updated-at"].dateTime = "2026-11-01T12:30:00Z";
elements["refresh-progress"].dataset.refreshMinute = "7";
const document = {
  hidden: false, activeElement: null,
  getElementById(id) { return elements[id] || null; },
  addEventListener(name, fn) { listeners.set(name, fn); }
};
const window = {
  setTimeout(fn, delay) {
    const id = ++nextId;
    timers.set(id, {fn, delay});
    return id;
  },
  clearTimeout(id) { timers.delete(id); },
  setInterval() { throw new Error("No debe existir el sondeo cada segundo"); },
};
vm.runInNewContext(
  fs.readFileSync("static/edition-status.js", "utf8"),
  {window, document, Date: FakeDate, Intl, URL, AbortController}
);
assert.equal(timers.size, 1, "una sola actualización pendiente");
let [id, task] = [...timers.entries()][0];
assert.equal(task.delay, 45050, "próximo minuto + margen de 50ms");
assert.ok(elements["refresh-progress"].attributes["aria-valuetext"]);
clock += task.delay;
timers.delete(id);
task.fn();
assert.equal(timers.size, 1, "se reprograma una sola vez");
assert.equal(elements["site-clock"].dateTime, new Date(clock).toISOString());
document.hidden = true;
listeners.get("visibilitychange")();
assert.equal(timers.size, 0, "se pausa en segundo plano");
clock += 90000;
document.hidden = false;
listeners.get("visibilitychange")();
assert.equal(timers.size, 1, "se recupera inmediatamente al volver");
assert.equal(elements["site-clock"].dateTime, new Date(clock).toISOString());
console.log("Reloj editorial: minuto, visibilidad y programación OK");
"""
        result = subprocess.run(
            ["node", "-e", script], text=True, capture_output=True,
            check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
