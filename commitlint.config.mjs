/** Conventional commits: `type(scope): subject`, e.g. `feat(i18n): translate the sign-in headers`. */
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Subjects may start with a product or proper name ("Infinity design v2", "French by default").
    "subject-case": [0],
    // Bodies may hold long links and command lines.
    "body-max-line-length": [0],
    "footer-max-line-length": [0],
  },
};
