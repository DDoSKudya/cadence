import { ClockIcon, GlobeAltIcon } from "@heroicons/vue/24/outline";
import type { Component } from "vue";

export type ProjectSettingPanelId = "language" | "timezone";

export interface ProjectSettingItem {
  id: string;
  titleKey: string;
  descriptionKey: string;
  icon: Component;
  panel?: ProjectSettingPanelId;
  route?: string;
}

export interface ProjectSettingGroup {
  id: string;
  titleKey: string;
  descriptionKey: string;
  icon: Component;
  iconClass: string;
  items: ProjectSettingItem[];
}

export const PROJECT_SETTING_GROUPS: ProjectSettingGroup[] = [
  {
    id: "interface",
    titleKey: "settings.hub.groups.interface.title",
    descriptionKey: "settings.hub.groups.interface.description",
    icon: GlobeAltIcon,
    iconClass: "project-settings-icon-interface",
    items: [
      {
        id: "language",
        titleKey: "settings.hub.items.language.title",
        descriptionKey: "settings.hub.items.language.description",
        icon: GlobeAltIcon,
        panel: "language",
      },
      {
        id: "timezone",
        titleKey: "settings.hub.items.timezone.title",
        descriptionKey: "settings.hub.items.timezone.description",
        icon: ClockIcon,
        panel: "timezone",
      },
    ],
  },
];

export function findProjectSettingItem(itemId: string | null) {
  if (!itemId) {
    return null;
  }
  for (const group of PROJECT_SETTING_GROUPS) {
    const item = group.items.find((entry) => entry.id === itemId);
    if (item) {
      return { group, item };
    }
  }
  return null;
}

export function findProjectSettingPanel(panelId: string | null) {
  const match = findProjectSettingItem(panelId);
  if (!match?.item.panel) {
    return null;
  }
  return match;
}
