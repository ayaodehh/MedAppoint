/** @type {import('next').NextConfig} */
const isDevelopment = process.env.NODE_ENV !== "production";

const nextConfig = {
  distDir: ".next-build",
  skipTrailingSlashRedirect: true,
  async headers() {
    const scriptSrc = ["'self'", "'unsafe-inline'"];
    const connectSrc = ["'self'", "http://127.0.0.1:8000", "http://localhost:8000"];

    if (isDevelopment) {
      scriptSrc.push("'unsafe-eval'");
      connectSrc.push("http://127.0.0.1:3000", "http://localhost:3000", "ws://127.0.0.1:3000", "ws://localhost:3000");
    }

    const csp = [
      "default-src 'self'",
      `script-src ${scriptSrc.join(" ")}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      `connect-src ${connectSrc.join(" ")}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "object-src 'none'",
      "upgrade-insecure-requests",
    ].join("; ");

    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  webpack: (config, { dev }) => {
    if (dev) {
      config.cache = false;
    }
    return config;
  },
};

module.exports = nextConfig;
