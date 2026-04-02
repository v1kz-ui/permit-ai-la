/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  wikiSidebar: [
    "intro",
    {
      type: "category",
      label: "Getting Started",
      items: [
        "getting-started/quickstart",
        "getting-started/environment-variables",
        "getting-started/deployment",
      ],
    },
    {
      type: "category",
      label: "Architecture",
      items: [
        "architecture/overview",
        "architecture/backend",
        "architecture/frontend",
        "architecture/database",
        "architecture/data-pipeline",
      ],
    },
    {
      type: "category",
      label: "Features",
      items: [
        "features/pathfinder-ai",
        "features/clearance-tracking",
        "features/bottleneck-prediction",
        "features/chat-assistant",
        "features/what-if-analysis",
        "features/document-management",
        "features/compliance-checker",
        "features/inspector-routing",
        "features/analytics",
        "features/notifications",
      ],
    },
    {
      type: "category",
      label: "API Reference",
      items: [
        "api-reference/overview",
        "api-reference/projects",
        "api-reference/clearances",
        "api-reference/pathfinder",
        "api-reference/inspections",
        "api-reference/analytics",
        "api-reference/admin",
        "api-reference/websocket",
      ],
    },
    {
      type: "category",
      label: "LA Permitting Guide",
      items: [
        "la-permitting/departments",
        "la-permitting/pathways",
        "la-permitting/clearance-types",
        "la-permitting/overlay-zones",
      ],
    },
    {
      type: "category",
      label: "Security",
      items: [
        "security/authentication",
        "security/audit-logging",
      ],
    },
    {
      type: "category",
      label: "Contributing",
      items: [
        "contributing/development",
        "contributing/ci-cd",
      ],
    },
  ],
};

module.exports = sidebars;
