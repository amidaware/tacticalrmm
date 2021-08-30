<template>
  <prism-editor class="editor" v-model="code" :highlight="highlighter" line-numbers @click="focusTextArea" />
</template>

<script>
// prism package imports
import { PrismEditor } from "vue-prism-editor";
import "vue-prism-editor/dist/prismeditor.min.css";

import { highlight, languages } from "prismjs/components/prism-core";
import "prismjs/components/prism-batch";
import "prismjs/components/prism-python";
import "prismjs/components/prism-powershell";
import "prismjs/themes/prism-tomorrow.css";

export default {
  name: "CodeEditor",
  components: {
    PrismEditor,
  },
  props: {
    code: !String,
    shell: !String,
  },
  setup(props) {
    function highlighter(code) {
      if (!props.shell) {
        return code;
      }
      let lang = props.shell === "cmd" ? "batch" : props.shell;
      return highlight(code, languages[lang]);
    }

    function focusTextArea() {
      document.getElementsByClassName("prism-editor__textarea")[0].focus();
    }

    return {
      //methods
      highlighter,
      focusTextArea,
    };
  },
};
</script>

<style>
/* required class */
.editor {
  /* we dont use `language-` classes anymore so thats why we need to add background and text color manually */
  background: #2d2d2d;
  color: #ccc;

  /* you must provide font-family font-size line-height. Example: */
  font-family: Fira code, Fira Mono, Consolas, Menlo, Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 5px;
  height: var(--prism-height);
}

/* optional class for removing the outline */
.prism-editor__textarea:focus {
  outline: none;
}

.prism-editor__textarea,
.prism-editor__container {
  width: 500em !important;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.prism-editor__container::-webkit-scrollbar,
.prism-editor__textarea::-webkit-scrollbar {
  display: none;
}

.prism-editor__editor {
  white-space: pre !important;
}
.prism-editor__container {
  overflow-x: auto !important;
}
</style>