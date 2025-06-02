module.exports = {
  allowedHosts: 'all',
  headers: {
    'Access-Control-Allow-Origin': '*',
  },
  proxy: {
    '/api': {
      target: 'http://localhost:4000',
      pathRewrite: { '^/api': '' },
      changeOrigin: true,
    },
  },
}; 