/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // In production the reverse proxy serves the frontend on the same origin
  // as the API, so no CORS issues.  In dev we point to localhost:8000.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:8000/api/:path*" },
    ];
  },
};

export default nextConfig;
