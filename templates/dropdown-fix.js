// Dropdown positioning fix - ensures suggestions appear above banner
(function() {
  function applyFix() {
    const box = document.getElementById('player-suggestions');
    if (!box) return;
    
    box.style.position = 'fixed';
    box.style.zIndex = '999999';
    box.style.left = '35px';
    box.style.top = '220px';
    box.style.width = '561px';
    box.style.maxHeight = '260px';
    box.style.overflow = 'auto';
  }
  
  // Apply immediately if DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyFix);
  } else {
    applyFix();
  }
  
  // Also apply after a short delay to catch dynamic elements
  setTimeout(applyFix, 100);
  setTimeout(applyFix, 500);
})();
