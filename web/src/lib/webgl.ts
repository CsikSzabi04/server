// Capability checks used to decide between the 3D mind-core and the 2D fallback.

export function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')),
    );
  } catch {
    return false;
  }
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

export function isSmallScreen(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 920px)').matches;
}
