#!/usr/bin/env node
/**
 * Builds packages/tailwind-config/infinity-nav.css, the anthracite theme of the Infinity Planning
 * navigation (top bar and sidebars), from the dark tokens of @makeplane/propel.
 *
 * propel only switches its tokens on :root, so a dark region inside a light page has to redeclare
 * them. This script copies propel's dark block under the .ip-nav class and replaces its neutral
 * scale with the group anthracite (docs/brand/charte.md). The active item of the navigation is a frost
 * white pill: .ip-nav-on switches its content back to the light tokens.
 *
 * Usage: node tools/brand/build-nav-theme.mjs  (run again after upgrading @makeplane/propel)
 */

import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(join(root, "packages/tailwind-config/package.json"));
const propelDir = dirname(require.resolve("@makeplane/propel/package.json"));
const variables = readFileSync(join(propelDir, "dist/styles/variables.css"), "utf8");

// Anthracite #2A2D2F for the surfaces, cadet blue grey #AEBDC1 for tertiary text, frost white
// #F5F9FA for primary text.
const NAV_NEUTRALS = {
  "--neutral-black": "oklch(0.2967 0.0053 229.9)",
  "--neutral-100": "oklch(0.2967 0.0053 229.9)",
  "--neutral-200": "oklch(0.325 0.006 230)",
  "--neutral-300": "oklch(0.355 0.007 230)",
  "--neutral-400": "oklch(0.385 0.008 230)",
  "--neutral-500": "oklch(0.42 0.009 230)",
  "--neutral-600": "oklch(0.47 0.01 228)",
  "--neutral-700": "oklch(0.53 0.012 225)",
  "--neutral-800": "oklch(0.6 0.015 220)",
  "--neutral-900": "oklch(0.68 0.018 218)",
  "--neutral-1000": "oklch(0.79 0.02 215)",
  "--neutral-1100": "oklch(0.88 0.012 215)",
  "--neutral-1200": "oklch(0.9799 0.0038 214)",
};

// The dark grey brand scale of packages/tailwind-config/index.css, instead of propel's blue.
const NAV_BRAND = {
  "--brand-50": "oklch(0.17 0.015 220)",
  "--brand-100": "oklch(0.2 0.015 220)",
  "--brand-200": "oklch(0.25 0.015 220)",
  "--brand-300": "oklch(0.31 0.015 220)",
  "--brand-400": "oklch(0.38 0.015 220)",
  "--brand-500": "oklch(0.44 0.015 220)",
  "--brand-600": "oklch(0.55 0.015 220)",
  "--brand-700": "oklch(0.66 0.015 220)",
  "--brand-800": "oklch(0.74 0.015 220)",
  "--brand-900": "oklch(0.87 0.015 220)",
  "--brand-1000": "oklch(0.93 0.015 220)",
  "--brand-1100": "oklch(0.965 0.015 220)",
  "--brand-1200": "oklch(0.985 0.015 220)",
  "--brand-default": "oklch(0.5 0.02 220)",
};

const OVERRIDES = { ...NAV_NEUTRALS, ...NAV_BRAND };

// The light theme overrides of packages/tailwind-config/index.css (keep both in sync).
const LIGHT_OVERRIDES = {
  "--neutral-100": "oklch(0.99 0.002 214)",
  "--neutral-200": "oklch(0.9799 0.0038 214)",
  "--neutral-300": "oklch(0.962 0.005 218)",
  "--neutral-400": "oklch(0.935 0.006 220)",
  "--neutral-500": "oklch(0.905 0.008 220)",
  "--neutral-600": "oklch(0.87 0.01 220)",
  "--neutral-700": "oklch(0.82 0.014 216)",
  "--neutral-800": "oklch(0.62 0.012 225)",
  "--neutral-900": "oklch(0.54 0.011 228)",
  "--neutral-1000": "oklch(0.46 0.009 230)",
  "--neutral-1100": "oklch(0.38 0.007 230)",
  "--neutral-1200": "oklch(0.2967 0.0053 229.9)",
  "--brand-50": "oklch(0.985 0.008 230)",
  "--brand-100": "oklch(0.968 0.008 230)",
  "--brand-200": "oklch(0.94 0.008 230)",
  "--brand-300": "oklch(0.9 0.008 230)",
  "--brand-400": "oklch(0.84 0.008 230)",
  "--brand-500": "oklch(0.76 0.008 230)",
  "--brand-600": "oklch(0.66 0.008 230)",
  "--brand-700": "oklch(0.55 0.008 230)",
  "--brand-800": "oklch(0.43 0.008 230)",
  "--brand-900": "oklch(0.25 0.008 230)",
  "--brand-1000": "oklch(0.21 0.008 230)",
  "--brand-1100": "oklch(0.18 0.008 230)",
  "--brand-1200": "oklch(0.15 0.008 230)",
  "--brand-default": "oklch(0.2967 0.0053 229.9)",
};

function block(css, opening) {
  const start = css.indexOf(opening);
  if (start === -1) throw new Error(`propel block not found: ${opening}`);
  let depth = 0;
  for (let i = css.indexOf("{", start); i < css.length; i++) {
    if (css[i] === "{") depth++;
    if (css[i] === "}" && --depth === 0) return css.slice(css.indexOf("{", start) + 1, i);
  }
  throw new Error(`propel block is not closed: ${opening}`);
}

const declarationsOf = (css) =>
  css
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("--"));

// Declarations of a block without those of its nested blocks (the @variant blocks of :root).
function topLevel(css) {
  let depth = 0;
  let out = "";
  for (const char of css) {
    if (char === "{") depth++;
    if (depth === 0) out += char;
    if (char === "}") depth--;
  }
  return out;
}

const withoutOverrides = (lines, overrides) => lines.filter((line) => !(line.split(":")[0] in overrides));

const declarations = withoutOverrides(declarationsOf(block(variables, "@variant dark {")), OVERRIDES);
const lightDeclarations = withoutOverrides(
  declarationsOf(topLevel(block(variables, ":root,\n  :host {"))),
  LIGHT_OVERRIDES
);

// Tailwind resolves its colour aliases (--text-color-secondary: var(--txt-secondary)...) on :root, so
// code that reads them directly would get the light values: redeclare them in the scope too.
const COLOR_ALIAS = /^--(text|background|border|outline|ring|fill|stroke|placeholder|caret|accent|divide)-color-/;
const aliases = declarationsOf(block(variables, "@theme inline {")).filter((line) => COLOR_ALIAS.test(line));

const body = [
  ...declarations,
  ...aliases,
  ...Object.entries(OVERRIDES).map(([name, value]) => `${name}: ${value};`),
  "color-scheme: dark;",
  "color: var(--txt-primary);",
];

const onBody = [
  ...lightDeclarations,
  ...aliases,
  ...Object.entries(LIGHT_OVERRIDES).map(([name, value]) => `${name}: ${value};`),
  "color-scheme: light;",
  "color: var(--txt-primary);",
];

const indent = (lines) => lines.map((line) => `    ${line}`).join("\n");

const output = `/*
 * Generated by tools/brand/build-nav-theme.mjs from the tokens of @makeplane/propel. Do not edit.
 * Anthracite theme of the Infinity Planning navigation: add the ip-nav class to a container, and
 * ip-nav-on to its active item (a frost white pill with light tokens).
 */
@layer base {
  .ip-nav {
${indent(body)}
  }

  .ip-nav .ip-nav-on {
${indent(onBody)}
  }
}
`;

writeFileSync(join(root, "packages/tailwind-config/infinity-nav.css"), output);
console.log(
  `infinity-nav.css: ${declarations.length} dark and ${lightDeclarations.length} light propel tokens, ${aliases.length} colour aliases`
);
