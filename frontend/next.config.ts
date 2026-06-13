import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 768, 1024, 1280, 1536],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
  },

  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },

  experimental: {
    optimizePackageImports: [
      '@/components/ui',
      'lucide-react',
      'recharts',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-dialog',
    ],
  },

  webpack(config, { isServer }) {
    if (!isServer) {
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          monaco: {
            test: /[\\/]node_modules[\\/]monaco-editor[\\/]/,
            name: 'monaco-editor',
            chunks: 'async',
            priority: 20,
            reuseExistingChunk: true,
          },
          reactflow: {
            test: /[\\/]node_modules[\\/]@?reactflow[\\/]/,
            name: 'reactflow',
            chunks: 'async',
            priority: 20,
            reuseExistingChunk: true,
          },
          recharts: {
            test: /[\\/]node_modules[\\/]recharts[\\/]/,
            name: 'recharts',
            chunks: 'async',
            priority: 15,
            reuseExistingChunk: true,
          },
          vendors: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
            priority: 10,
            reuseExistingChunk: true,
          },
          common: {
            minChunks: 2,
            priority: 5,
            reuseExistingChunk: true,
          },
        },
      };
    }
    return config;
  },

  poweredByHeader: false,

  reactStrictMode: true,
};

export default withNextIntl(nextConfig);
