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


document.addEventListener('DOMContentLoaded', function () {
  const deleteModal = document.getElementById('deleteModal');
  const deleteCowTag = document.getElementById('deleteCowTag');
  const deleteForm = document.getElementById('deleteCowForm');
  const successToast = new bootstrap.Toast(document.getElementById('deleteSuccessToast'));
  const errorToast = new bootstrap.Toast(document.getElementById('deleteErrorToast'));

  let deleteUrl = '';
  let targetRow = null;

  deleteModal.addEventListener('show.bs.modal', function (event) {
    const trigger = event.relatedTarget;
    const earTag = trigger.getAttribute('data-ear-tag');
    deleteUrl = trigger.getAttribute('data-url');
    targetRow = trigger.closest('tr');
    deleteCowTag.textContent = earTag;
  });

  deleteForm.addEventListener('submit', function (e) {
    e.preventDefault();
    fetch(deleteUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
    .then(response => {
      if (!response.ok) throw new Error('Delete failed');
      return response.json();
    })
    .then(data => {
      if (targetRow) {
        targetRow.style.transition = 'opacity 0.4s ease-out';
        targetRow.style.opacity = '0';
        setTimeout(() => {
          targetRow.remove();
          const modalInstance = bootstrap.Modal.getInstance(deleteModal);
          modalInstance.hide();
          successToast.show();
        }, 400);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      const modalInstance = bootstrap.Modal.getInstance(deleteModal);
      modalInstance.hide();
      errorToast.show();
    });
  });
});
