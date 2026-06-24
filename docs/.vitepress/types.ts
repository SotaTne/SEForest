import type { UserConfig, MarkdownOptions } from "vitepress";

export type MarkdownConfig = NonNullable<MarkdownOptions["config"]>;
export type PluginOption = NonNullable<
  NonNullable<UserConfig["vite"]>["plugins"]
>[0];
