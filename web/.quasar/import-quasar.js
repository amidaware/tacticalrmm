/**
 * THIS FILE IS GENERATED AUTOMATICALLY.
 * DO NOT EDIT.
 *
 * You are probably looking on adding startup/initialization code.
 * Use "quasar new boot <name>" and add it there.
 * One boot file per concern. Then reference the file(s) in quasar.conf.js > boot:
 * boot: ['file', ...] // do not add ".js" extension to it.
 *
 * Boot files are your "main.js"
 **/

import lang from 'quasar/lang/en-us'

import iconSet from 'quasar/icon-set/material-icons'


import Vue from 'vue'

import {Quasar,Dialog,Loading,LoadingBar,Meta,Notify} from 'quasar'


Vue.use(Quasar, { config: {"loadingBar":{"color":"red","size":"4px"},"notify":{"position":"top","timeout":2000,"textColor":"white","actions":[{"icon":"close","color":"white"}]}},lang: lang,iconSet: iconSet,plugins: {Dialog,Loading,LoadingBar,Meta,Notify} })
