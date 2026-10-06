import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";

// Layer order: types < config < api < hooks < components < app
const layers = ["types", "config", "api", "hooks", "components", "app"];
const upward = (i) =>
  layers.slice(i + 1).flatMap((l) => [`**/${l}`, `**/${l}/*`, `**/${l}/**`]);
const layerRules = layers.map((layer, i) => ({
  files: [`src/${layer}/**/*.{ts,tsx}`],
  rules: {
    "no-restricted-imports": [
      "error",
      { patterns: upward(i).map((group) => ({ group: [group], message: `${layer} must not import a higher layer` })) },
    ],
  },
}));

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-explicit-any": "error",
      "no-console": "error",
    },
  },
  ...layerRules,
  { files: ["*.config.{js,ts}"], languageOptions: { globals: { ...globals.node } } },
);
