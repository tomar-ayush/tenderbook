import Script from 'next/script';
import shell from './shell';

// The design's markup and its script, unchanged: the script fills #view from /api/* in the browser.
export default function Page() {
  return (
    <>
      <div style={{ display: 'contents' }} dangerouslySetInnerHTML={{ __html: shell }} />
      <Script src="/app.js" strategy="afterInteractive" />
    </>
  );
}
