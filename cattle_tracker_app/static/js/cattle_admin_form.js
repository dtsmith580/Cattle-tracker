document.addEventListener('DOMContentLoaded', function () {
  const methodField = document.querySelector('[name="breeding_method"]');
  const naturalSire = document.querySelector('.field-sire');
  const aiSire = document.querySelector('.field-herd_sire');

  function toggleSireFields() {
    const method = methodField?.value;
    console.log("🐮 toggleSireFields triggered");
    console.log("Selected Method:", method);

    if (naturalSire) {
      naturalSire.style.display = method === 'natural' ? 'block' : 'none';
      console.log("🔁 Natural Sire toggled:", method === 'natural');
    }
    if (aiSire) {
      aiSire.style.display = method === 'ai' ? 'block' : 'none';
      console.log("🔁 AI Sire toggled:", method === 'ai');
    }
  }

  if (methodField) {
    methodField.addEventListener('change', toggleSireFields);
    toggleSireFields(); // run on page load
  }
});
