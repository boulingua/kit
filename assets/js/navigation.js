// Keep native disclosure controls usable without JavaScript; add Escape support.
document.querySelectorAll('.navigation-dropdown').forEach(dropdown => {
  dropdown.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      dropdown.open = false;
      dropdown.querySelector('summary').focus();
    }
  });
});
