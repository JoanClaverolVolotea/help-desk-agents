interface ErrorBannerProps {
  message: string;
}

export default function ErrorBanner({ message }: ErrorBannerProps): JSX.Element | null {
  if (!message) {
    return null;
  }

  return <aside className="error-banner">{message}</aside>;
}
