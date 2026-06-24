import { defineConfig } from "vitepress";
import { serveStaticIndexPages, staticCopyPlugins } from "./plugin";
import type { MarkdownConfig } from "./types";

const addTargetSelfToStaticLinks: MarkdownConfig = (md) => {
  const defaultLinkOpen =
    md.renderer.rules.link_open ??
    ((tokens, idx, options, _env, self) =>
      self.renderToken(tokens, idx, options));

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    const href = token.attrGet("href");

    if (
      href?.startsWith("./Forest_Document/") ||
      href?.startsWith("./Project_Forest_Hints/")
    ) {
      token.attrSet("target", "_self");
    }

    return defaultLinkOpen(tokens, idx, options, env, self);
  };
};

export default defineConfig({
  base: "/SEForest/",
  title: "SEForest",
  description:
    "ソフトウェア工学II「樹状整列」のドキュメントと参考資料をまとめた入口",
  cleanUrls: true,
  ignoreDeadLinks: true,
  markdown: {
    config(md) {
      addTargetSelfToStaticLinks(md);
    },
  },
  vite: {
    plugins: [staticCopyPlugins, serveStaticIndexPages()],
  },
  themeConfig: {
    docFooter: {
      prev: false,
      next: false,
    },
    nav: [
      { text: "ホーム", link: "/" },
      {
        text: "要求仕様書",
        link: "/Forest_Document/Requirement/",
        target: "_self",
      },
      {
        text: "Forest JavaDoc",
        link: "/Project_Forest_Hints/Forest/JavaDoc/",
        target: "_self",
      },
    ],
    sidebar: [
      {
        text: "Forest ドキュメント",
        items: [
          { text: "ホーム", link: "/Forest_Document/", target: "_self" },
          {
            text: "要求仕様書",
            link: "/Forest_Document/Requirement/",
            target: "_self",
          },
          {
            text: "開発計画書",
            link: "/Forest_Document/DevelopmentPlan/",
            target: "_self",
          },
          {
            text: "基本設計書",
            link: "/Forest_Document/BasicDesign/",
            target: "_self",
          },
          {
            text: "詳細設計書",
            link: "/Forest_Document/DetailDesign/",
            target: "_self",
          },
          {
            text: "テスト仕様書",
            link: "/Forest_Document/TestSpecification/",
            target: "_self",
          },
          {
            text: "テスト結果",
            link: "/Forest_Document/TestResult/",
            target: "_self",
          },
          {
            text: "開発実績",
            link: "/Forest_Document/DevelopmentResult/",
            target: "_self",
          },
          {
            text: "プログラム",
            link: "/Forest_Document/Program/",
            target: "_self",
          },
          {
            text: "マニュアル",
            link: "/Forest_Document/Manual/",
            target: "_self",
          },
        ],
      },
      {
        text: "Project Forest ヒント",
        items: [
          {
            text: "Forest JavaDoc",
            link: "/Project_Forest_Hints/Forest/JavaDoc/",
            target: "_self",
          },
          {
            text: "Forest by MVC JavaDoc",
            link: "/Project_Forest_Hints/Forest_by_MVC/JavaDoc/",
            target: "_self",
          },
        ],
      },
    ],
  },
});
