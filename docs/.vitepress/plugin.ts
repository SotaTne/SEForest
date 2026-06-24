import { viteStaticCopy } from "vite-plugin-static-copy";
import type { PluginOption } from "./types";

export const staticCopyPlugins: PluginOption = viteStaticCopy({
  targets: [
    {
      src: ["../Forest_Document/**/*", "!../Forest_Document/**/.DS_Store"],
      dest: ".",
    },
    {
      src: [
        "../Project_Forest_Hints/**/*",
        "!../Project_Forest_Hints/**/.DS_Store",
      ],
      dest: ".",
    },
  ],
}) as PluginOption;

export function serveStaticIndexPages(): PluginOption {
  return {
    name: "serve-static-index-pages",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (!req.url) {
          next();
          return;
        }

        const [pathname, search] = req.url.split("?");
        const staticRoots = [
          "/SEForest/Forest_Document/",
          "/SEForest/Project_Forest_Hints/",
          "/Forest_Document/",
          "/Project_Forest_Hints/",
        ];

        if (
          staticRoots.some((root) => pathname.startsWith(root)) &&
          pathname.endsWith("/")
        ) {
          req.url = `${pathname}index.html${search ? `?${search}` : ""}`;
        }

        next();
      });
    },
  };
}
