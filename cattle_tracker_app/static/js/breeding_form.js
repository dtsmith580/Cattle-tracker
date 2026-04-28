// breeding_form.js
// Handles field visibility logic for the Breeding Record form

document.addEventListener('DOMContentLoaded', function () {
  // Cache field wrappers by name
  const methodField = document.querySelector('[name="method"]');
  const cleanupMethodField = document.querySelector('[name="cleanup_method"]');

  const bullField = document.querySelector('.field-bull');
  const herdSireField = document.querySelector('.field-herd-sire');
  const cleanupMethodWrapper = document.querySelector('.field-cleanup-method');
  const cleanupSireField = document.querySelector('.field-cleanup-sire');
  const cleanupHerdSireField = document.querySelector('.field-cleanup-herd-sire');

  console.log("🐮 breeding_form.js loaded");

  // Function to show/hide fields based on breeding method
  function toggleBreedingFields() {
    const method = methodField?.value;

    // Always hide everything initially
    if (bullField) {
      bullField.style.display = 'none';
      const select = bullField.querySelector('select');
      if (select) select.value = '';
    }
    if (herdSireField) {
      herdSireField.style.display = 'none';
      const select = herdSireField.querySelector('select');
      if (select) select.value = '';
    }
    if (cleanupMethodWrapper) cleanupMethodWrapper.style.display = 'none';
    if (cleanupSireField) cleanupSireField.style.display = 'none';
    if (cleanupHerdSireField) cleanupHerdSireField.style.display = 'none';

    // Show based on method
    if (method === 'natural') {
      if (bullField) bullField.style.display = 'block';
      if (cleanupMethodWrapper) cleanupMethodWrapper.style.display = 'block';
    } else if (method === 'ai') {
      if (herdSireField) herdSireField.style.display = 'block';
      if (cleanupMethodWrapper) cleanupMethodWrapper.style.display = 'block';
    }
  }

  // Function to show/hide cleanup sire fields based on cleanup method
  function toggleCleanupFields() {
    const method = cleanupMethodField?.value;

    if (cleanupSireField) {
      cleanupSireField.style.display = (method === 'natural') ? 'block' : 'none';
      if (method !== 'natural') {
        const select = cleanupSireField.querySelector('select');
        if (select) select.value = '';
      }
    }

    if (cleanupHerdSireField) {
      cleanupHerdSireField.style.display = (method === 'ai') ? 'block' : 'none';
      if (method !== 'ai') {
        const select = cleanupHerdSireField.querySelector('select');
        if (select) select.value = '';
      }
    }
  }

  if (methodField) {
    methodField.addEventListener('change', toggleBreedingFields);
    toggleBreedingFields(); // Run on load
  }

  if (cleanupMethodField) {
    cleanupMethodField.addEventListener('change', toggleCleanupFields);
    toggleCleanupFields(); // Run on load
  }
});
