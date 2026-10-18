import { createApp } from "vue";
import { Button, Cell, Segmented, Switch, Tag } from "tdesign-mobile-vue";
import Dialog from "tdesign-mobile-vue/es/dialog/index.mjs";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "tdesign-mobile-vue/es/style/index.css";
import "./styles.css";
import App from "./App.vue";

const app = createApp(App);
[Button, Cell, Segmented, Switch, Tag, Dialog].forEach((component) => {
  app.use(component);
});
app.mount("#app");

