function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = document.createElement('div');
  icon.innerHTML = type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ';
  icon.style.fontWeight = 'bold';
  icon.style.fontSize = '16px';
  
  const text = document.createElement('div');
  text.textContent = message;
  
  toast.appendChild(icon);
  toast.appendChild(text);
  
  container.appendChild(toast);

  // Auto remove after 4 seconds
  setTimeout(() => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => {
      toast.remove();
    });
  }, 4000);
}

// Intercept status text content changes on #status if possible,
// but for cleaner integration we'll expose showToast globally 
// and update HTML logic to use it.
window.showToast = showToast;
