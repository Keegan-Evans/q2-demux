// ----------------------------------------------------------------------------
// Copyright (c) 2016-2022, QIIME 2 development team.
//
// Distributed under the terms of the Modified BSD License.
//
// The full license is in the file LICENSE, distributed with this software.
// ----------------------------------------------------------------------------

var path = require('path');
var webpack = require('webpack');

module.exports = {
  entry: {
    app: './src/main.js',
    vendor: ['d3']
  },
  plugins: [
    new webpack.optimize.CommonsChunkPlugin('vendor', 'dist/vendor.bundle.js'),
    new webpack.optimize.UglifyJsPlugin({
      compress: { warnings: false },
      mangle: { except: ['init'] }
    }),
    new webpack.NoErrorsPlugin(),
  ],
  output: {
    path: __dirname,
    filename: 'dist/bundle.js',
    libraryTarget: 'var',
    library: 'app'
  },
  resolve: {
    extensions: ['', '.js']
  },
  module: {
    loaders: [
      {
        loader: 'babel-loader',
        exclude: /node_modules/,
        query: {
          presets: ['es2015']
        }
      }
    ]
  },
};
