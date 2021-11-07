import { Notify } from "quasar";

export function isValidThreshold(warning, error, diskcheck = false) {
  if (warning === 0 && error === 0) {
    Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold or Error Threshold need to be set" });
    return false;
  }

  if (!diskcheck && warning > error && warning > 0 && error > 0) {
    Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold must be less than Error Threshold" });
    return false;
  }

  if (diskcheck && warning < error && warning > 0 && error > 0) {
    Notify.create({ type: "negative", timeout: 2000, message: "Warning Threshold must be more than Error Threshold" });
    return false;
  }

  return true;
}

export function validateEventID(val) {
  if (val === null || val.toString().replace(/\s/g, "") === "") {
    return false;
  } else if (val === "*") {
    return true;
  } else if (!isNaN(val)) {
    return true;
  } else {
    return false;
  }
}

// validate script return code
export function validateRetcode(val, done) {
  /^\d+$/.test(val) ? done(val) : done();
}