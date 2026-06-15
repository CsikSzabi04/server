import { Component, type ReactNode } from 'react';

interface Props {
  fallback: ReactNode;
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

// Catches any runtime failure inside the 3D scene (e.g. WebGL context loss) and
// renders the 2D fallback instead, so the centre is never blank.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.warn('[MindCore] 3D failed — falling back to 2D reactor:', error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
