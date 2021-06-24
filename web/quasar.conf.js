require('dotenv').config();
const path = require('path');

module.exports = function () {
  return {
    supportTS: false,
    // https://quasar.dev/quasar-cli/cli-documentation/prefetch-feature
    // preFetch: true,
    boot: [
      'axios',
    ],
    // https://quasar.dev/quasar-cli/quasar-conf-js#Property%3A-css
    css: [
      'app.sass'
    ],
    // https://github.com/quasarframework/quasar/tree/dev/extras
    extras: [
      // 'ionicons-v4',
      'mdi-v5',
      'fontawesome-v5',
      // 'eva-icons',
      // 'themify',
      // 'line-awesome',
      // 'roboto-font-latin-ext', // this or either 'roboto-font', NEVER both!

      'roboto-font', // optional, you are not bound to it
      'material-icons', // optional, you are not bound to it
    ],

    // Full list of options: https://quasar.dev/quasar-cli/quasar-conf-js#Property%3A-build
    build: {
      env: { DEV_API: process.env.DEV_URL, PROD_API: process.env.PROD_URL, DOCKER_BUILD: process.env.DOCKER_BUILD },
      vueRouterMode: 'history', // available values: 'hash', 'history'
      distDir: "dist/",
      devtool: process.env.NODE_ENV === "production" ? "cheap-module-eval-source-map" : "source-map",

      // Add dependencies for transpiling with Babel (Array of regexes)
      // (from node_modules, which are by default not transpiled).
      // Does not applies to modern builds.
      // transpileDependencies: [],

      // rtl: false, // https://quasar.dev/options/rtl-support
      // preloadChunks: false,
      // showProgress: false,
      // gzip: true,
      // analyze: true,

      // Options below are automatically set depending on the env, set them if you want to override
      // extractCSS: false,

      // https://quasar.dev/quasar-cli/cli-documentation/handling-webpack
      extendWebpack(cfg) {
        cfg.resolve.alias = {
          ...cfg.resolve.alias,
          "@": path.resolve(__dirname, './src'),
        }
      },
    },

    // Full list of options: https://quasar.dev/quasar-cli/quasar-conf-js#Property%3A-devServer
    devServer: {
      https: false,
      host: process.env.DEV_HOST,
      port: process.env.DEV_PORT,
      public: process.env.APP_URL,
      open: false
    },

    // https://quasar.dev/quasar-cli/quasar-conf-js#Property%3A-framework
    framework: {
      iconSet: 'material-icons', // Quasar icon set
      lang: 'en-US', // Quasar language pack

      // Quasar plugins
      plugins: [
        'Dialog',
        'Loading',
        'LoadingBar',
        'Meta',
        'Notify'
      ],
      config: {
        loadingBar: {
          size: "4px"
        },
        notify: {
          position: "top",
          timeout: 2000,
          textColor: "white",
          actions: [{ icon: "close", color: "white" }]
        },
        loading: {
          delay: 100
        }
      }
    },

    // animations: 'all', // --- includes all animations
    // https://quasar.dev/options/animations
    animations: [],

    // https://quasar.dev/quasar-cli/developing-ssr/configuring-ssr
    ssr: {
      pwa: false
    }
  }
}
