// @ts-check
const { themes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "PermitAI LA",
  tagline: "AI-powered fire rebuild permit tracking for Los Angeles",
  favicon: "img/favicon.ico",
  url: "https://permitai-la.github.io",
  baseUrl: "/",
  organizationName: "permitai-la",
  projectName: "wiki",
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          routeBasePath: "/",
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: "PermitAI LA",
        items: [
          {
            type: "docSidebar",
            sidebarId: "wikiSidebar",
            position: "left",
            label: "Documentation",
          },
          {
            href: "https://github.com/SongNiviworksmo/Permit-AI-for-LA",
            label: "GitHub",
            position: "right",
          },
        ],
      },
      footer: {
        style: "dark",
        links: [
          {
            title: "Docs",
            items: [
              { label: "Getting Started", to: "/getting-started/quickstart" },
              { label: "Architecture", to: "/architecture/overview" },
              { label: "API Reference", to: "/api-reference/overview" },
            ],
          },
          {
            title: "LA Resources",
            items: [
              {
                label: "LADBS",
                href: "https://www.ladbs.org",
              },
              {
                label: "LA City Planning",
                href: "https://planning.lacity.gov",
              },
              {
                label: "ZIMAS",
                href: "https://zimas.lacity.org",
              },
            ],
          },
        ],
        copyright: `Copyright ${new Date().getFullYear()} PermitAI LA. Built with Docusaurus.`,
      },
      prism: {
        theme: themes.github,
        darkTheme: themes.dracula,
        additionalLanguages: ["python", "bash", "json", "typescript"],
      },
    }),
};

module.exports = config;
