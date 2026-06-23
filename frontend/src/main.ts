import "@fontsource-variable/inter";

import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./app/App.vue";
import { router } from "./app/router";
import { i18n } from "./i18n";
import { useLocaleStore } from "./stores/locale";
import "./styles/index.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(i18n);
app.use(router);
app.mount("#app");

void useLocaleStore(pinia).load();
