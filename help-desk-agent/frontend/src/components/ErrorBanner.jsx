export default function ErrorBanner({ message }) {
  if (!message) {
    return null;
  }

  return <aside className="error-banner">{message}</aside>;
}
