 (function() {
  // Toggle between static display and inline form
  function toggleEdit(card) {
    const staticDisplay = card.querySelector('.static-display');
    const inlineForm = card.querySelector('#inline-form');
    if (staticDisplay && inlineForm) {
      staticDisplay.classList.toggle('hidden');
      inlineForm.classList.toggle('hidden');
    }
  }

  // Delegate click events for edit toggles
  document.addEventListener('click', function(e) {
    const toggleBtn = e.target.closest('.edit-toggle');
    if (toggleBtn) {
      const card = toggleBtn.closest('.profile-card');
      if (card) {
        toggleEdit(card);
      }
    }
  });

  // On HTMX content swap, reset visibility
  document.body.addEventListener('htmx:afterSwap', function(e) {
    const card = e.detail.target.closest('.profile-card');
    if (card) {
      const staticDisplay = card.querySelector('.static-display');
      const inlineForm = card.querySelector('#inline-form');
      if (staticDisplay && inlineForm) {
        staticDisplay.classList.remove('hidden');
        inlineForm.classList.add('hidden');
      }
    }
  });
 
})();