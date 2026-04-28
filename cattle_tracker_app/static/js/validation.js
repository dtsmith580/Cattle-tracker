function validateImageSize(input, maxMB = 2, callback = null) {
  const file = input.files[0];
  if (!file) return;

  const maxBytes = maxMB * 1024 * 1024;
  if (file.size > maxBytes) {
    alert(`Image must be less than ${maxMB}MB.`);
    input.value = "";
    return;
  }

  if (callback && typeof callback === "function") {
    callback(input);
  }
}
