import type { NextConfig } from "next";

// GitHub Pages는 프로젝트 사이트를 /<repo> 하위 경로로 서빙한다.
// 로컬 dev(NEXT_PUBLIC_BASE_PATH 미설정)에서는 빈 값 → 루트(/)로 동작.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export", // 정적 export → web/out/ 산출 (GitHub Pages용)
  basePath: basePath || undefined,
  images: { unoptimized: true }, // 정적 export에서는 이미지 최적화 비활성
  trailingSlash: true, // /path → /path/index.html 매핑 (Pages 호환)
};

export default nextConfig;
