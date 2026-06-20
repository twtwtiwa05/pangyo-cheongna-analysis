import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "판교 vs 청라 업무지구 비교분석",
  description:
    "데이터로 진단하는 업무지구의 성공과 실패 — 판교테크노밸리와 인천 청라국제도시 정량 비교",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <head>
        {/* 한글 본문 폰트: Pretendard (dynamic-subset, 필요한 글리프만 로드) */}
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css"
        />
      </head>
      <body className="h-full m-0 overflow-hidden">{children}</body>
    </html>
  );
}
