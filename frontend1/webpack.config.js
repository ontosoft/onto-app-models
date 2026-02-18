module.exports = {
  resolve: {
  //  extensions: [".js", ".jsx", ".json", ".ts", ".tsx",".owl" ],
    fallback: { "url": require.resolve("url/") }
  },
  rules: [
    {
      test: /\.owl/,
      type: 'asset/resource',
      use: '@svgr/webpack?-prettier,-svgo,+titleProp,+ref![path]'
    }
  ]
};