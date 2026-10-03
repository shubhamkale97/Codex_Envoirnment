// Fetch the year from verified internet time; never read the browser's clock.
async function refreshCopyrightYear() {
  try {
    const response = await fetch('/api/time', { cache: 'no-store' });
    if (!response.ok) return;
    const { year } = await response.json();
    if (Number.isInteger(year) && year >= 2026 && year <= 2200) {
      document.getElementById('copyrightYear').textContent = String(year);
    }
  } catch { /* Retain the displayed year during an internet outage. */ }
}
refreshCopyrightYear();
setInterval(refreshCopyrightYear, 60 * 60 * 1000);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refreshCopyrightYear();
});
