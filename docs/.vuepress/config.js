const { description } = require('../package')

module.exports = {
  base: '/tacticalrmm/',
  title: 'Tactical RMM',
  description: description,

  head: [
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { name: 'apple-mobile-web-app-capable', content: 'yes' }],
    ['meta', { name: 'apple-mobile-web-app-status-bar-style', content: 'black' }]
  ],
  themeConfig: {
    repo: '',
    editLinks: false,
    docsDir: '',
    editLinkText: '',
    lastUpdated: false,
    nav: [
      {
        text: 'Guide',
        link: '/guide/',
      }
    ],
    sidebar: {
      '/guide/': [
        {
          title: 'Guide',
          collapsable: false,
          children: [
            '',
          ]
        }
      ],
    }
  },
  plugins: [
    //'@vuepress/plugin-back-to-top',
    //'@vuepress/plugin-medium-zoom',
  ]
}
