// Legacy redirect: window.DEFAULT_WORKSPACE points to authentic pipeline export
// All fabricated / mock values (e.g., M084, LOT-D2-08, LOT-D2-15) have been permanently removed.
if (typeof window !== 'undefined') {
  window.DEFAULT_WORKSPACE = (typeof window.REAL_WORKSPACE_DATA !== 'undefined') ? window.REAL_WORKSPACE_DATA : null;
}
